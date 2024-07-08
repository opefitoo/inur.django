from datetime import date

from django.test import TestCase

from dependence.invoicing import LongTermCareInvoiceFile, LongTermCareInvoiceLine, LongTermCareInvoiceItem
from dependence.longtermcareitem import LongTermPackage
from invoices.models import Patient


class LongTermCareInvoiceFileTestCase(TestCase):
    def setUp(self):
        self.patient_john = Patient.objects.create(id=1309,
                                                   name="John",
                                                   is_under_dependence_insurance=True,
                                                   date_of_exit=None)
        LongTermPackage.objects.create(dependence_level=1, package=True, code="TESTCODE", description="TESTDESC")
        # Setup test data
        self.invoice_file = LongTermCareInvoiceFile.objects.create(
            invoice_start_period=date(2023, 1, 1),
            invoice_end_period=date(2023, 1, 31),
            patient=self.patient_john
        )
        # Create a line and an item with errors
        LongTermCareInvoiceLine.objects.create(
            invoice=self.invoice_file,
            refused_by_insurance=True,
            start_period=date(2023, 1, 1),
            end_period=date(2023, 1, 31),
        )
        LongTermCareInvoiceItem.objects.create(
            invoice=self.invoice_file,
            refused_by_insurance=True,
            care_date=date(2023, 1, 1),
            long_term_care_package=LongTermPackage.objects.get(code="TESTCODE"))

    def test_copy_prestations_in_error_to_new_invoice(self):
        # Call the method under test
        new_invoice = self.invoice_file.copy_prestations_in_error_to_new_invoice()

        # Assertions
        self.assertNotEqual(new_invoice.id, self.invoice_file.id, "A new invoice should be created.")
        self.assertEqual(new_invoice.patient, self.patient_john, "The new invoice should have the same patient.")
        self.assertEqual(LongTermCareInvoiceLine.objects.filter(invoice=new_invoice).count(), 1, "The new invoice should have one line.")
        self.assertEqual(LongTermCareInvoiceItem.objects.filter(invoice=new_invoice).count(), 1, "The new invoice should have one item.")
        self.assertFalse(LongTermCareInvoiceLine.objects.filter(invoice=new_invoice, refused_by_insurance=True).exists(), "The new invoice should not have lines with errors.")
        self.assertFalse(LongTermCareInvoiceItem.objects.filter(invoice=new_invoice, refused_by_insurance=True).exists(), "The new invoice should not have items with errors.")
