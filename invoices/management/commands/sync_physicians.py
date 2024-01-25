from django.core.management.base import BaseCommand

from invoices.actions.physicians import open_file_and_sync_physicians_from_tsv


class Command(BaseCommand):
    help = 'Synchronize physicians from a TSV file'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='The path to the TSV file')

    def handle(self, *args, **options):
        file_path = options['file_path']
        open_file_and_sync_physicians_from_tsv(file_path)
        self.stdout.write(self.style.SUCCESS('Successfully synchronized physicians'))
