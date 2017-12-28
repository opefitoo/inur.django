import httplib2
import uuid
import datetime

from apiclient import discovery
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials
from django.conf import settings
from django.utils import timezone


class PrestationGoogleCalendar:
    summary = 'Prestations'
    calendar = None

    def get_credentials(self):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(self._json_keyfile_path,
                                                                       scopes=["https://www.googleapis.com/auth/calendar"])

        return credentials

    def __init__(self, json_keyfile_path=None):
        """
        Handles credentials and builds the google service.

        :param _json_keyfile_path: Path
        :param user_email: String
        :raise ValueError:
        """
        self._json_keyfile_path = json_keyfile_path or settings.GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE

        credentials = self.get_credentials()
        http = credentials.authorize(httplib2.Http())
        self._service = discovery.build('calendar', 'v3', http=http)
        self._set_calendar()

    def _set_calendar(self):
        calendar = self._get_existing_calendar()
        if calendar is None:
            calendar = self._create_calendar()

        self.calendar = calendar

    def _get_existing_calendar(self):
        calendar = None
        calendar_list = self._service.calendarList().list().execute()
        for existing_calendar in calendar_list['items']:
            if existing_calendar['summary'] == self.summary:
                calendar = existing_calendar

        return calendar

    def _create_calendar(self):
        calendar = {
            'summary': self.summary,
            'description': 'Nurse. Prestations created in the future',
            'timeZone': settings.TIME_ZONE
        }

        return self._service.calendars().insert(body=calendar).execute()

    @staticmethod
    def _get_event_id(prestation_id):
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, 'NURSE_PRESTATION_GCALENDAR' + str(prestation_id)).hex)

    def update_event(self, prestation):
        now = timezone.now()
        if prestation.date <= now:
            return None

        event_id = self._get_event_id(prestation_id=prestation.id)
        descr_line = "<b>%s</b> %s<br>"
        description = descr_line % ('Patient:', prestation.invoice_item.patient)
        description += descr_line % ('Invoice Item:', prestation.invoice_item)
        description += descr_line % ('CareCode:', prestation.carecode)
        summary = '%s %s' % (prestation.id, prestation)
        location = prestation.invoice_item.patient.address

        start_datetime = prestation.date
        end_datetime = prestation.date + datetime.timedelta(minutes=20)
        event_body = {
            'id': event_id,
            'summary': summary,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_datetime.isoformat(),
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
            }
        }

        event = self.get_event(event_id=event_id)
        if event is None:
            event = self._service.events().insert(calendarId=self.calendar['id'], body=event_body).execute()
        else:
            event = self._service.events().update(calendarId=self.calendar['id'], eventId=event_id,
                                                  body=event_body).execute()

        return event

    def delete_event(self, prestation_id):
        event_id = self._get_event_id(prestation_id=prestation_id)
        try:
            event = self._service.events().delete(calendarId=self.calendar['id'], eventId=event_id).execute()
        except HttpError:
            event = None

        return event

    def get_event(self, event_id):
        try:
            event = self._service.events().get(calendarId=self.calendar['id'], eventId=event_id).execute()
        except HttpError:
            event = None

        return event

    def update_calendar_permissions(self, email, has_access):
        rules = self._service.acl().list(calendarId=self.calendar['id']).execute()
        user_rules = [d for d in rules['items'] if d['scope']['value'] == email]
        permissions_granted = len(user_rules)
        if self.calendar is not None:
            if has_access and 0 == permissions_granted:
                rule = self._get_acl_rule(email)
                self._service.acl().insert(calendarId=self.calendar['id'], body=rule).execute()
            elif not has_access and 0 < permissions_granted:
                for user_rule in user_rules:
                    self._service.acl().delete(calendarId=self.calendar['id'], ruleId=user_rule['id']).execute()
        else:
            return None

    @staticmethod
    def _get_acl_rule(email):
        rule = {
            'scope': {
                'type': 'user',
                'value': email,
            },
            'role': 'writer'
        }

        return rule
