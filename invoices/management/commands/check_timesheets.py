
from django.core.management.base import BaseCommand

from invoices.processors.timesheets import get_door_events_for_employee


class Command(BaseCommand):
    help = 'Checks for employees timesheet'

    def handle(self, *args, **options):
        process_result = get_door_events_for_employee()

        self.stdout.write(self.style.SUCCESS('Process result %s') % process_result)
        return
