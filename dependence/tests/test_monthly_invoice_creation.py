from datetime import date

from django.test import TestCase

from dependence.invoicing import LongTermCareInvoiceFile, LongTermCareMonthlyStatement
from invoices.models import Patient


class TestLongTermCareInvoiceFile(TestCase):
    def setUp(self):
        # first remove patient with id 1509 and 1510 if they exist
        Patient.objects.filter(id=1509).delete()
        Patient.objects.filter(id=1510).delete()

        self.patient_john = Patient.objects.create(id=1509, name="John", is_under_dependence_insurance=True,
                                                   date_of_exit=None)
        self.patient_kevin = Patient.objects.create(id=1510, name="Kevin", is_under_dependence_insurance=True,
                                                    date_of_exit=None)
        #self.monthly_statement = LongTermCareMonthlyStatement.objects.create(year=2022, month=1)
        self.invoice_file_1 = LongTermCareInvoiceFile.objects.create(
            invoice_start_period=date(2022, 1, 1),
            invoice_end_period=date(2022, 1, 31),
            patient_id=1509  # Replace with an actual Patient id
        )
        self.invoice_file_2 = LongTermCareInvoiceFile.objects.create(
            invoice_start_period=date(2022, 1, 1),
            invoice_end_period=date(2022, 1, 31),
            patient_id=1510  # Replace with an actual Patient id
        )

    def test_link_invoice_to_monthly_statement(self):
        id_of_monthly_statement = self.invoice_file_1.link_operation_invoice_to_monthly_statement()
        #self.assertEqual(self.invoice_file_1.link_to_monthly_statement, self.monthly_statement)
        self.invoice_file_2.link_operation_invoice_to_monthly_statement(id_of_monthly_statement)
        self.assertEqual(self.invoice_file_2.link_to_monthly_statement, self.invoice_file_1.link_to_monthly_statement)
        monthly_statement = LongTermCareMonthlyStatement.objects.get(id=id_of_monthly_statement)
        self.assertEqual(monthly_statement.get_invoices.count(), 2)
