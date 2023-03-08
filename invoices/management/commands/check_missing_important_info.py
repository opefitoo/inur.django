from django.core.management.base import BaseCommand

from invoices.processors.missing_infos import search_for_missing_important_infos


class Command(BaseCommand):
    help = 'Checks for missing important information'

    def handle(self, *args, **options):
        search_result = search_for_missing_important_infos()
        self.stdout.write(self.style.SUCCESS('Process result %s') % search_result)
        return
