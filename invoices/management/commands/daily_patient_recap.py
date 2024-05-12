import datetime

from django.core.management.base import BaseCommand

from invoices.events import Event


class Command(BaseCommand):
    help = 'Sends the daily patient recap'

    def handle(self, *args, **kwargs):
        events_by_patient = {}
        # loop through all events today's events
        for event in Event.objects.filter(day=datetime.date.today()).order_by('time_start_event'):
            if event.patient not in events_by_patient:
                events_by_patient[event.patient] = []
            events_by_patient[event.patient].append(event)

        string_events_by_patient = ""

        for patient, events in events_by_patient.items():
            print(f"Patient: {patient}")
            string_events_by_patient += f"Patient: {patient}\n"
            for event in events:
                if event.event_address:
                    string_events_by_patient += f"  {event} at {event.time_start_event} assigned to {event.employees} in address {event.event_address}\n"
                else:
                    string_events_by_patient += f"  {event} at {event.time_start_event} assigned to {event.employees}\n"
                print(f"  {event} assigned to {event.employees} in address {event.event_address}")

        print(string_events_by_patient)
        # log output notify_system_via_google_webhook execution result
        #exec_result = notify_system_via_google_webhook(string_events_by_patient)
        #self.stdout.write(self.style.SUCCESS('Notify result %s') % exec_result)
        self.stdout.write(self.style.SUCCESS('Done'))
