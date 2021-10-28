import uuid
import datetime

import pytz
from apiclient import discovery
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from django.conf import settings

import logging
import sys
from rq import Queue
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
        if data.get('id'):
            description += descr_line % (u'Sur LU ID:', data.get('id'))
        if data.get('notes') and len(data.get('notes')) > 0:
            description += descr_line % ('Notes:', data.get('notes'))
        summary = '%s - %s' % (data.get('patient'), ','.join(u.abbreviation for u in data.get('event_employees')))

        naive_date = datetime.datetime(data.get('day').year,
                                       data.get('day').month, data.get('day').day,
                                       data.get('time_start_event').hour,
                                       data.get('time_start_event').minute,
                                       data.get('time_start_event').second)
        localized = pytz.timezone('Europe/Luxembourg').localize(naive_date)
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
                'dateTime': pytz.timezone('Europe/Luxembourg').localize(naive_end_date).isoformat(),
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

    def update_event(self, event):
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
            location = "%s, %s %s, %s" % (event.patient.address,
                                          event.patient.zipcode,
                                          event.patient.city,
                                          event.patient.country)
        description += descr_line % (u'Adresse:', address)
        description += descr_line % (u'Tél Patient:', event.patient.phone_number)
        if event.id:
            description += descr_line % (u'Sur LU ID:', event.id)
        if event.notes and len(event.notes) > 0:
            description += descr_line % ('Notes:', event.notes)
        summary = '%s - %s' % (event.patient, event.employees.abbreviation)

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

        attendees_list = []
        if event.event_assigned.count() > 1:
            for u in event.event_assigned.all():
                attendees_list.append({'email': '%s' % u.assigned_additional_employee.user.email})

        event_body = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': {
                'dateTime': localized.isoformat(),
            },
            'end': {
                'dateTime': pytz.timezone('Europe/Luxembourg').localize(naive_end_date).isoformat(),
            },
            'attendees': attendees_list
        }

        gmail_event = self.get_event(event_id=event.calendar_id, calendar_id=event.employees.user.email)
        if gmail_event is None:
            gmail_event = self._service.events().insert(calendarId=event.employees.user.email,
                                                        body=event_body).execute()
        else:
            gmail_event = self._service.events().update(calendarId=event.employees.user.email,
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

    def delete_event(self, evt_instance):
        # print("Trying to delete %s from %s" % (evt_instance.calendar_id, evt_instance))
        # sys.stdout.flush()
        try:
            gmail_event = self._service.events().delete(calendarId=evt_instance.employees.user.email,
                                                        eventId=evt_instance.calendar_id).execute()
        except HttpError as e:
            # print("An error happened when trying to delete event %s - exception %s" % (evt_instance.calendar_id, e))
            # sys.stdout.flush()
            return
        # print("Successfully delete GCalendar event %s" % gmail_event)
        # sys.stdout.flush()
        return gmail_event

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
