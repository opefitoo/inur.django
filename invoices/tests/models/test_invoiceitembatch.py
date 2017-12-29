from django.utils import timezone
from django.test import TestCase
from django.contrib.auth.models import User

from invoices.models import CareCode, Patient, Prestation, InvoiceItem, InvoiceItemBatch
from invoices.timesheet import Employee, JobPosition


class InvoiceItemBatchTestCase(TestCase):
    def test_string_representation(self):
        date = timezone.now()
        batch = InvoiceItemBatch(start_date=date,
                                 end_date=date)

        self.assertEqual(str(batch), 'from %s to %s' % (batch.start_date, batch.end_date))

    def test_validate_dates(self):
        data = {
            'start_date': timezone.now().replace(month=1, day=10),
            'end_date': timezone.now().replace(month=6, day=10)
        }

        self.assertEqual(InvoiceItemBatch.validate_dates(data), {})

        data['start_date'] = data['start_date'].replace(month=6, day=10)
        self.assertEqual(InvoiceItemBatch.validate_dates(data), {})

        data['start_date'] = data['start_date'].replace(month=6, day=11)
        self.assertEqual(InvoiceItemBatch.validate_dates(data), {'end_date': 'End date must be bigger than Start date'})
