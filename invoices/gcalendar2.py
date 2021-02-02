import uuid
import datetime

import pytz
from apiclient import discovery
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from oauth2client.service_account import ServiceAccountCredentials
from django.conf import settings
from django.utils import timezone


class PrestationGoogleCalendarSurLu:
    summary = 'Prestations'
    calendar = None

    def get_credentials(self):
        SCOPES = ['https://www.googleapis.com/auth/sqlservice.admin',
                  'https://www.googleapis.com/auth/calendar']

        credentials = service_account.Credentials.from_service_account_file(
            self._json_keyfile_path, scopes=SCOPES)

        delegated_credentials = credentials.with_subject('mehdi@sur.lu')
        return delegated_credentials

    def __init__(self, json_keyfile_path=None):
        """
        Handles credentials and builds the google service.

        :param _json_keyfile_path: Path
        :param user_email: String
        :raise ValueError:
        """
        self._json_keyfile_path = json_keyfile_path or settings.GOOGLE_DRIVE_STORAGE_JSON_KEY_FILE2

        credentials = self.get_credentials()
        # http = credentials.authorize(httplib2.Http())
        self._service = discovery.build('calendar', 'v3', credentials=credentials)
        # self._set_calendar()

    def _set_calendar(self):
        calendar = self._get_existing_calendar()
        if calendar is None:
            calendar = self._create_calendar()

        self.calendar = calendar

    def list_all_calendars(self):
        page_token = None
        while True:
            calendar_list = self._service.calendarList().list(pageToken=page_token).execute()
            for calendar_list_entry in calendar_list['items']:
                print
                calendar_list_entry['summary']
            page_token = calendar_list.get('nextPageToken')
            if not page_token:
                break

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
    def _get_event_id(event_id):
        return str(uuid.uuid5(uuid.NAMESPACE_DNS, 'NURSE_PRESTATION_GCALENDAR' + str(event_id)).hex)

    def update_event(self, event):
        event_id = self._get_event_id(event_id=event.id)
        descr_line = "<b>%s</b> %s<br>"
        description = descr_line % ('Patient:', event.patient)
        if event.at_office:
            address = event.event_address
            location = address
        elif not event.at_office and event.event_address:
            address = event.event_address
            location = address
        else:
            address = event.patient.address
            location = "%s,%s %s, %s" % (event.patient.address,
                                     event.patient.zipcode,
                                     event.patient.city,
                                     event.patient.country)
        description += descr_line % (u'Adresse:', address)
        description += descr_line % (u'Tél Patient:', event.patient.phone_number)
        if len(event.notes) > 0:
            description += descr_line % ('Notes:', event.notes)
        summary = '%s %s' % (event.id, event.patient)

        naive_date = datetime.datetime(event.day.year,
                                       event.day.month, event.day.day,
                                       event.time_start_event.hour,
                                       event.time_start_event.minute,
                                       event.time_start_event.second)
        localized = pytz.timezone('Europe/Luxembourg').localize(naive_date)
        naive_end_date = datetime.datetime(event.day.year,
                                           event.day.month, event.day.day,
                                           event.time_end_event.hour,
                                           event.time_end_event.minute,
                                           event.time_end_event.second)

        event_body = {
            'id': event_id,
            'summary': summary,
            'description': description,
            'location': location,
            'start': {
                'dateTime': localized.isoformat(),
            },
            'end': {
                'dateTime': pytz.timezone('Europe/Luxembourg').localize(naive_end_date).isoformat(),
            }
        }

        gmail_event = self.get_event(event_id=event_id, calendar_id=event.employees.user.email)
        if gmail_event is None:
            gmail_event = self._service.events().insert(calendarId=event.employees.user.email,
                                                        body=event_body).execute()
        else:
            gmail_event = self._service.events().update(calendarId=event.employees.user.email, eventId=event_id,
                                                        body=event_body).execute()

        if 'id' in gmail_event.keys():
            return gmail_event
        else:
            raise ValueError("error during sync with google calendar %s" % gmail_event)

    def delete_event(self, event):
        event_id = self._get_event_id(event_id=event.id)
        try:
            gmail_event = self._service.events().delete(calendarId=event.employees.user.email, eventId=event_id).execute()
        except HttpError:
            raise ValueError("error during sync with google calendar %s" % gmail_event)

        return gmail_event

    def get_event(self, event_id, calendar_id):
        try:
            event = self._service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        except HttpError:
            return None
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
