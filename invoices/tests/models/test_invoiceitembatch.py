from datetime import datetime

from django.utils import timezone
from django.test import TestCase
from django.test import override_settings
from django.contrib.auth.models import User

from invoices.models import CareCode, Patient, Prestation, InvoiceItem, InvoiceItemBatch
from invoices.employee import Employee, JobPosition


class InvoiceItemBatchTestCase(TestCase):
    def setUp(self):
        date = datetime.now()
        self.patient = Patient.objects.create(first_name='first name',
                                              name='name')

        date.replace(hour=0, minute=0)
        self.december_invoices = [
            InvoiceItem.objects.create(invoice_number='936 some invoice_number',
                                       invoice_date=date.replace(month=12, day=1),
                                       patient=self.patient),
            InvoiceItem.objects.create(invoice_number='10',
                                       invoice_date=date.replace(month=12, day=15),
                                       patient=self.patient),
            InvoiceItem.objects.create(invoice_number='058',
                                       invoice_date=date.replace(month=12, day=31),
                                       patient=self.patient)
        ]

        self.december_invoices_private = [
            InvoiceItem.objects.create(invoice_number='946 some invoice_number',
                                       invoice_date=date.replace(month=12, day=1),
                                       patient=self.patient,
                                       is_private=True),
            InvoiceItem.objects.create(invoice_number='11',
                                       invoice_date=date.replace(month=12, day=15),
                                       patient=self.patient,
                                       is_private=True)
        ]

        self.october_invoices = [
            InvoiceItem.objects.create(invoice_number='147',
                                       invoice_date=date.replace(month=10, day=1),
                                       patient=self.patient),
            InvoiceItem.objects.create(invoice_number='259',
                                       invoice_date=date.replace(month=10, day=10),
                                       patient=self.patient)
        ]

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

    # def test_associated_items(self):
    #     date = datetime.now()
    #     date.replace(hour=0, minute=0)
    #
    #     date.replace(month=12, day=1)
    #     batch_december = InvoiceItemBatch.objects.create(start_date=date.replace(month=12, day=1),
    #                                                      end_date=date.replace(month=12, day=31))
    #     #F    IXME
    #     #self.assertEqual(len(self.december_invoices), batch_december.invoice_items.count())
    #
    #     # batch_october = InvoiceItemBatch.objects.create(start_date=date.replace(month=10, day=1),
    #     #                                                 end_date=date.replace(month=10, day=23))
    #     # self.assertEqual(len(self.october_invoices), batch_october.invoice_items.count())
    #     #
    #     # batch_all = InvoiceItemBatch.objects.create(start_date=date.replace(month=10, day=1),
    #     #                                             end_date=date.replace(month=12, day=31))
    #     # self.assertEqual(0, batch_all.invoice_items.count())
    #     #
    #     # batch_december.end_date = date.replace(month=12, day=25)
    #     # batch_december.save()
    #     # self.assertEqual(len(self.december_invoices)-1, batch_december.invoice_items.count())
    #
    #     batch_december.delete()
    #     batch_october.delete()
    #     batch_all.delete()
