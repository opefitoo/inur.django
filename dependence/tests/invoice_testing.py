from datetime import datetime

from django.test import TestCase

from dependence.actions.monthly import create_monthly_invoice
from dependence.detailedcareplan import MedicalCareSummaryPerPatient
from dependence.invoicing import LongTermCareInvoiceFile, LongTermCareInvoiceLine
from invoices.models import Patient


class TestMonthlyInvoice(TestCase):
    fixtures = ['longtermpackage.json']

    def setUp(self):
        self.patient = Patient.objects.create(name="John", is_under_dependence_insurance=True, date_of_exit=None)
        self.month = 2
        self.year = 2022


    def test_create_monthly_invoice(self):

        # Create a medical care summary for the patient
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient,
                                                    date_of_decision=datetime(2022, 1, 10),
                                                    date_of_evaluation=datetime(2022, 1, 1),
                                                    date_of_request=datetime(2021, 12, 1),
                                                    date_of_notification=datetime(2022, 1, 11),
                                                    date_of_notification_to_provider=datetime(2022, 1, 12),
                                                    plan_number="123456789",
                                                    decision_number="123456789",
                                                    start_of_support=datetime(2022, 1, 1),
                                                    level_of_needs=1)

        # Call the create_monthly_invoice method
        statement = create_monthly_invoice(self.patient, self.month, self.year)

        # Check that a LongTermCareMonthlyStatement was created for the correct month and year
        self.assertEqual(statement.month, self.month)
        self.assertEqual(statement.year, self.year)

        # Check that a LongTermCareInvoiceFile was created for the patient and period
        invoice = LongTermCareInvoiceFile.objects.get(patient=self.patient, invoice_start_period=datetime(2022, 2, 1),
                                                      invoice_end_period=datetime(2022, 2, 28))

        # Check that a LongTermCareInvoiceLine was created for the invoice and period
        line = LongTermCareInvoiceLine.objects.get(invoice=invoice,
                                                   start_period=datetime(2022, 2, 1),
                                                   end_period=datetime(2022, 2, 28))

        # Check that the LongTermCarePackage on the invoice line matches the level of needs from the medical care summary
        self.assertEqual(line.long_term_care_package.dependence_level, 1)
