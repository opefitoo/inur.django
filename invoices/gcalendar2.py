import datetime
import logging
import os
import sys
from zoneinfo import ZoneInfo

from apiclient import discovery
from constance import config
from django.conf import settings
from django.db.models import Q
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from rq import Queue

from invoices.employee import Employee
from invoices.enums.event import EventTypeEnum
from worker import conn

logger = logging.getLogger('console')


class PrestationGoogleCalendarSurLu:
    summary = 'Prestations'
    calendar = None

    def get_credentials(self):
        SCOPES = ['https://www.googleapis.com/auth/sqlservice.admin',
                  'https://www.googleapis.com/auth/calendar']

        credentials = service_account.Credentials.from_service_account_file(
            self._json_keyfile_path, scopes=SCOPES)
        delegated_credentials = credentials.with_subject(os.environ.get('GOOGLE_EMAIL_CREDENTIALS', None))
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

    def update_event_through_data(self, data):
        descr_line = "<b>%s</b> %s<br>"

        description = descr_line % ('Patient:', data.get('patient'))
        if data.get('at_office'):
            address = data.get('event_address')
            location = address
        elif not data.get('at_office') and data.get('event_address'):
            address = data.get('event_address')
            location = address
        else:
            address = data.get('patient').address
            location = "%s, %s %s, %s" % (data.get('patient').address,
                                          data.get('patient').zipcode,
                                          data.get('patient').city,
                                          data.get('patient').country)
        description += descr_line % (u'Adresse:', address)
        description += descr_line % (u'Tél Patient:', data.get('patient').phone_number)
        if data.get('patient').additional_phone_number:
            description += descr_line % (u'Tél 2 Patient:', data.get('patient').additional_phone_number)
        if data.get('id'):
            description += descr_line % (u'Sur LU ID:', data.get('id'))
        if data.get('notes') and len(data.get('notes')) > 0:
            description += descr_line % ('Notes:', data.get('notes'))
        summary = '%s - %s' % (data.get('patient'), ','.join(u.abbreviation for u in data.get('event_employees')))

        localized = datetime.datetime(data.get('day').year,
                                      data.get('day').month, data.get('day').day,
                                      data.get('time_start_event').hour,
                                      data.get('time_start_event').minute,
                                      data.get('time_start_event').second).astimezone(ZoneInfo("Europe/Luxembourg"))
        naive_end_date = datetime.datetime(data.get('day').year,
                                           data.get('day').month, data.get('day').day,
                                           data.get('time_end_event').hour,
                                           data.get('time_end_event').minute,
                                           data.get('time_end_event').second)

        attendees_list = []
        if len(data.get('event_employees')) > 0:
            for u in data.get('event_employees'):
                attendees_list.append({'email': '%s' % u.user.email})
        event_body = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': {
                'dateTime': localized.isoformat(),
            },
            'end': {
                'dateTime': naive_end_date.astimezone(ZoneInfo("Europe/Luxembourg")).isoformat(),
            },
            'attendees': attendees_list
        }

        gmail_event = None
        if data.get('calendar_id'):
            gmail_event = self.get_event(event_id=data.get('calendar_id'),
                                         calendarId=data.get('event_employees')[0].user.email)
        if gmail_event is None:
            gmail_event = self._service.events().insert(calendarId=data.get('event_employees')[0].user.email,
                                                        body=event_body).execute()
        else:
            gmail_event = self._service.events().update(calendarId=data.get('event_employees')[0],
                                                        eventId=data.get('calendar_id'),
                                                        body=event_body).execute()

        if 'id' in gmail_event.keys():
            # logger.info("gmail event created %s", gmail_event)
            # print("*** gmail event created %s" % gmail_event)
            # sys.stdout.flush()
            return gmail_event
        else:
            raise ValueError("error during sync with google calendar %s" % gmail_event)

    def update_events_sur_id(self, event):
        if event.employees:
            calendar_id = event.employees.user.email
        else:
            calendar_id = config.GENERAL_CALENDAR_ID
        gmail_event = self.get_event(event_id=event.calendar_id, calendar_id=calendar_id)
        event_body = {
            'summary': gmail_event['summary'],
            'description': gmail_event['description'] + "<b>%s</b> %s<br>" % (u'Sur LU ID:', event.id),
            'location': gmail_event['location'],
            'start': gmail_event['start'],
            'end': gmail_event['end'],
        }
        return self._service.events().update(calendarId=calendar_id,
                                             eventId=event.calendar_id,
                                             body=event_body).execute()

    def update_event(self, event):
        descr_line = "<b>%s</b> %s<br>"
        description = descr_line
        address = None
        if event.patient:
            description = descr_line % ('Patient:', event.patient)
        if event.at_office:
            address = event.event_address
            location = address
        elif not event.at_office and event.event_address:
            address = event.event_address
            location = address
        elif event.patient and event.patient.get_full_address_date_based(current_date=event.day):
            address = event.patient.get_full_address_date_based(current_date=event.day)
            location = "%s" % address
        if address:
            description += descr_line % (u'Adresse:', address)
        if event.patient:
            description += descr_line % (u'Tél Patient:', event.patient.phone_number)
            if event.patient.additional_phone_number:
                description += descr_line % (u'Tél 2 Patient:', event.patient.additional_phone_number)
        if event.id:
            description += descr_line % (u'Sur LU ID:', event.id)
        if event.notes and len(event.notes) > 0:
            description += descr_line % ('Notes:', event.notes)
        if event.event_report and len(event.event_report) > 0:
            description += descr_line % ('Rapport de soin:', event.event_report)
        if event.employees and event.patient:
            summary = '%s - %s' % (event.patient, event.employees.abbreviation)
        elif event.employees and not event.patient:
            summary = '%s - %s' % (event.employees.abbreviation, event.notes)
        elif not event.employees and event.patient:
            summary = '%s - %s' % (event.patient, event.notes)
        localized = None
        if EventTypeEnum.BIRTHDAY != event.event_type_enum:
            localized = datetime.datetime(event.day.year,
                                          event.day.month, event.day.day,
                                          event.time_start_event.hour,
                                          event.time_start_event.minute,
                                          event.time_start_event.second).astimezone(ZoneInfo("Europe/Luxembourg"))
            naive_end_date = datetime.datetime(event.day.year,
                                               event.day.month, event.day.day,
                                               event.time_end_event.hour,
                                               event.time_end_event.minute,
                                               event.time_end_event.second)

            attendees_list = []
            if event.id and event.event_assigned.count() > 1:
                for u in event.event_assigned.all():
                    attendees_list.append({'email': '%s' % u.assigned_additional_employee.user.email})

            event_body = {
                'summary': "! ANNULÉ %s !" % ('\u0336'.join(summary) + '\u0336') if event.state in [5,6] else summary,
                'description': description,
                'location': location,
                'status': "cancelled" if 5 == event.state else "confirmed",
                'start': {
                    'dateTime': localized.isoformat(),
                },
                'end': {
                    'dateTime': naive_end_date.astimezone(ZoneInfo("Europe/Luxembourg")).isoformat(),
                },
                'attendees': attendees_list
            }
        else:
            localized = datetime.datetime(event.day.year,
                                          event.day.month, event.day.day,
                                          8,
                                          0,
                                          0).astimezone(ZoneInfo("Europe/Luxembourg"))
            naive_end_date = datetime.datetime(event.day.year,
                                               event.day.month, event.day.day,
                                               20,
                                               0,
                                               0)
            event_body = {
                'summary': "! ANNULÉ %s !" % ('\u0336'.join(summary) + '\u0336') if event.state in [5,6] else summary,
                'description': description,
                'location': location,
                'start': {
                    'dateTime': localized.isoformat(),
                },
                # 5 is cancelled
                'status': "cancelled" if 5 == event.state else "confirmed",
                'end': {
                    'dateTime': naive_end_date.astimezone(ZoneInfo("Europe/Luxembourg")).isoformat(),
                },
            }

        if event.employees:
            calendar_id = event.employees.user.email
        else:
            calendar_id = config.GENERAL_CALENDAR_ID

        gmail_event = self.get_event(event_id=event.calendar_id, calendar_id=calendar_id)
        if gmail_event is None:
            gmail_event = self._service.events().insert(calendarId=calendar_id,
                                                        body=event_body).execute()
        else:
            gmail_event = self._service.events().update(calendarId=calendar_id,
                                                        eventId=event.calendar_id,
                                                        body=event_body).execute()

        if 'id' in gmail_event.keys():
            # logger.info("gmail event created %s", gmail_event)
            # print("*** gmail event created %s" % gmail_event)
            # sys.stdout.flush()
            return gmail_event
        else:
            raise ValueError("error during sync with google calendar %s" % gmail_event)

    def q_delete_event(self, evt_instance):
        q = Queue(connection=conn)
        q_r = q.enqueue(self.delete_event, evt_instance)
        print("Queue result %s" % q_r)
        sys.stdout.flush()

    def delete_event_by_google_id(self, calendar_id, event_id, dry_run=True):
        if dry_run:
            e = self._service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            print("Pretending that I delete event: %s on Google %s" % (event_id, e))
            return e
        event = self.get_event(calendar_id=calendar_id, event_id=event_id)
        if event and 'cancelled' == event['status']:
            return
        if event:
            try:
                gmail_event = self._service.events().delete(calendarId=calendar_id,
                                                        eventId=event_id).execute()
                return gmail_event
            except HttpError as e:
                if e.resp.status == 410 and 'Resource has been deleted' in e.content:
                     print("Event %s already deleted" % event_id)
                     return
                else:
                    raise ValueError("Problem de connexion", e)
        return event

    def delete_event(self, evt_instance):
        if evt_instance.employees:
            return self.delete_event_by_google_id(calendar_id=evt_instance.employees.user.email,
                                              event_id=evt_instance.calendar_id,
                                              dry_run=False)
        return self.delete_event_by_google_id(calendar_id=config.GENERAL_CALENDAR_ID,
                                              event_id=evt_instance.calendar_id,
                                              dry_run=False)

    def list_event_with_sur_id(self):
        employees = Employee.objects.filter(end_contract=None).filter(~Q(abbreviation='XXX'))
        inur_event_ids = []
        for emp in employees:
            g_events = self._service.events().list(calendarId=emp.user.email, q="SUR LU ID",
                                                   timeMin="2022-07-21T10:00:00-00:00").execute()

            for g_event in g_events['items']:
                description = g_event['description']
                _inur_event_id = description.split("Sur LU ID:</b>")[1].split("<br>")[0]
                inur_event_ids.append({'email': emp.user.email, 'gId': g_event['id'], 'inurId': _inur_event_id,
                                       'htmlLink': g_event['htmlLink'],
                                       'start': g_event['start'], 'end': g_event['end']})
        return inur_event_ids

    def delete_all_events_from_calendar(self, calendar_id):
        # FIXME: hardcoded date to be replaced
        events = self._service.events().list(calendarId=calendar_id, timeMin='2021-11-01T10:00:00-00:00').execute()
        counter = 0
        for event in events['items']:
            self._service.events().delete(calendarId=calendar_id,
                                          eventId=event['id']).execute()
            counter += 1
        return counter

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
