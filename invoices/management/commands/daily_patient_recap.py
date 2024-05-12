import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from invoices.events import Event
from invoices.notifications import notify_system_via_google_webhook


class Command(BaseCommand):
    help = 'Sends the daily patient recap'

    def handle(self, *args, **kwargs):
        events_by_patient = {}
        # Get tomorrow's date
        tomorrow = timezone.now().date() + datetime.timedelta(days=1)

        # loop through all events of tomorrow's date
        for event in Event.objects.filter(day=tomorrow).order_by('time_start_event'):
            if event.patient not in events_by_patient:
                events_by_patient[event.patient] = []
            events_by_patient[event.patient].append(event)

        string_events_by_patient = ""

        for patient, events in events_by_patient.items():
            print(f"Patient: {patient}")
            string_events_by_patient += f"Patient: {patient}\n"
            for event in events:
                if event.event_address or event.event_address.strip() != "":
                    string_events_by_patient += f"  *passage de {event.time_start_event} assigné à {event.employees} !!ATTENTION ADRESSE!! {event.event_address} *\n"
                else:
                    string_events_by_patient += f"  passage de {event.time_start_event} assigné à {event.employees}\n"
                print(f"  {event} assigned to {event.employees} in address {event.event_address}")

        print(string_events_by_patient)
        # log output notify_system_via_google_webhook execution result
        exec_result = notify_system_via_google_webhook(string_events_by_patient)
        #exec_result = notify_system_via_google_webhook(string_events_by_patient)
        self.stdout.write(self.style.SUCCESS('Notify result %s' % exec_result))
        self.stdout.write(self.style.SUCCESS('Done'))
