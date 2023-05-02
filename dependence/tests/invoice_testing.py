from _decimal import Decimal
from datetime import datetime

from django.test import TestCase

from dependence.actions.monthly import create_monthly_invoice
from dependence.detailedcareplan import MedicalCareSummaryPerPatient
from dependence.invoicing import LongTermCareInvoiceFile
from invoices.models import Patient


class TestMonthlyInvoice(TestCase):
    fixtures = ['longtermpackage.json']

    def setUp(self):
        self.patient_john = Patient.objects.create(name="John", is_under_dependence_insurance=True, date_of_exit=None)
        self.patient_david = Patient.objects.create(name="David", is_under_dependence_insurance=True, date_of_exit=None)
        self.patient_lucy = Patient.objects.create(name="Lucy", is_under_dependence_insurance=True, date_of_exit=None)
        self.month = 4
        self.year = 2023


    def test_create_monthly_invoice(self):

        # Create a medical care summary for the patient
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_john,
                                                    date_of_decision=datetime(2022, 1, 10),
                                                    date_of_evaluation=datetime(2022, 1, 1),
                                                    date_of_request=datetime(2021, 12, 1),
                                                    date_of_notification=datetime(2022, 1, 11),
                                                    date_of_notification_to_provider=datetime(2022, 1, 12),
                                                    plan_number="123456789",
                                                    decision_number="123456789",
                                                    start_of_support=datetime(2022, 1, 1),
                                                    level_of_needs=1)
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_david,
                                                    date_of_decision=datetime(2022, 1, 10),
                                                    date_of_evaluation=datetime(2022, 1, 1),
                                                    date_of_request=datetime(2021, 12, 1),
                                                    date_of_notification=datetime(2022, 1, 11),
                                                    date_of_notification_to_provider=datetime(2022, 1, 12),
                                                    plan_number="123456789",
                                                    decision_number="123456789",
                                                    start_of_support=datetime(2022, 1, 1),
                                                    level_of_needs=3)
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_lucy,
                                                    date_of_decision=datetime(2022, 1, 10),
                                                    date_of_evaluation=datetime(2022, 1, 1),
                                                    date_of_request=datetime(2021, 12, 1),
                                                    date_of_notification=datetime(2022, 1, 11),
                                                    date_of_notification_to_provider=datetime(2022, 1, 12),
                                                    plan_number="123456789",
                                                    decision_number="123456789",
                                                    start_of_support=datetime(2022, 1, 1),
                                                    level_of_needs=12)

        patient_list = [self.patient_john, self.patient_david, self.patient_lucy]

        # Call the create_monthly_invoice method
        statement = create_monthly_invoice(patient_list, self.month, self.year)

        # Check that a LongTermCareMonthlyStatement was created for the correct month and year
        self.assertEqual(statement.month, self.month)
        self.assertEqual(statement.year, self.year)

        # Check that a LongTermCareInvoiceFile was created for the patient and period
        invoice = LongTermCareInvoiceFile.objects.get(patient=self.patient_john, invoice_start_period=datetime(2023, 4, 1),
                                                      invoice_end_period=datetime(2023, 4, 30))

        # Check that a LongTermCareInvoiceLine was created for the invoice and period
        # line = LongTermCareInvoiceLine.objects.get(invoice=invoice,
        #                                            start_period=datetime(2023, 4, 1),
        #                                            end_period=datetime(2023, 4, 30))
        self.assertEqual(statement.calculate_total_price(), Decimal('22187.90'))
        #self.assertEqual(line.calculate_price(), Decimal('1723.47'))

        # Check that the LongTermCarePackage on the invoice line matches the level of needs from the medical care summary
        #self.assertEqual(line.long_term_care_package.dependence_level, 1)
