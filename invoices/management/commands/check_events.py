from django.core.management.base import BaseCommand

from invoices.notifications import notify_system_via_google_webhook
from invoices.processors.birthdays import process_and_generate


class Command(BaseCommand):
    help = 'Checks for patient birthdays'

    def handle(self, *args, **options):
        process_result = process_and_generate(30)
        message = "Process result %s" % process_result
        self.stdout.write(self.style.SUCCESS('Process result %s') % process_result)
        # log output notify_system_via_google_webhook execution result
        exec_result = notify_system_via_google_webhook(message)
        self.stdout.write(self.style.SUCCESS('Notify result %s') % exec_result)
