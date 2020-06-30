from django.core.management.base import BaseCommand

from invoices.processors.birthdays import process_and_generate


class Command(BaseCommand):
    help = 'Checks for patient birthdays'

    def handle(self, *args, **options):
        process_result = process_and_generate()
        self.stdout.write(self.style.SUCCESS('Process result %s') % process_result)
        return
