from _decimal import Decimal
from datetime import date

from django.test import TestCase

from dependence.actions.monthly import create_monthly_invoice
from dependence.activity import LongTermMonthlyActivityDetail, LongTermMonthlyActivity
from dependence.detailedcareplan import MedicalCareSummaryPerPatient
from dependence.invoicing import LongTermCareInvoiceFile
from dependence.longtermcareitem import LongTermCareItem
from invoices.models import Patient


class TestMonthlyInvoice(TestCase):
    fixtures = ['longtermpackage.json', 'longtermitems.json']

    def setUp(self):
        self.patient_john = Patient.objects.create(id=1309, name="John", is_under_dependence_insurance=True,
                                                   date_of_exit=None)
        self.patient_david = Patient.objects.create(name="David", is_under_dependence_insurance=True, date_of_exit=None)
        self.patient_lucy = Patient.objects.create(name="Lucy", is_under_dependence_insurance=True, date_of_exit=None)
        self.month = 4
        self.year = 2023

    def test_create_monthly_invoice(self):
        """
        Test that a monthly invoice is created for a patient
        @return: None
        """
        # Create a medical care summary for the patient
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_john,
                                                    date_of_decision=date(2022, 1, 10),
                                                    date_of_evaluation=date(2022, 1, 1),
                                                    date_of_request=date(2021, 12, 1),
                                                    date_of_notification=date(2022, 1, 11),
                                                    date_of_notification_to_provider=date(2022, 1, 12),
                                                    plan_number="123456789",
                                                    decision_number="123456789",
                                                    start_of_support=date(2022, 1, 1),
                                                    level_of_needs=1,
                                                    nature_package=1)
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_david,
                                                    date_of_decision=date(2022, 1, 10),
                                                    date_of_evaluation=date(2022, 1, 1),
                                                    date_of_request=date(2021, 12, 1),
                                                    date_of_notification=date(2022, 1, 11),
                                                    date_of_notification_to_provider=date(2022, 1, 12),
                                                    plan_number="123456789",
                                                    decision_number="123456789",
                                                    start_of_support=date(2022, 1, 1),
                                                    level_of_needs=3,
                                                    nature_package=3)
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_lucy,
                                                    date_of_decision=date(2022, 1, 10),
                                                    date_of_evaluation=date(2022, 1, 1),
                                                    date_of_request=date(2021, 12, 1),
                                                    date_of_notification=date(2022, 1, 11),
                                                    date_of_notification_to_provider=date(2022, 1, 12),
                                                    plan_number="123456789",
                                                    decision_number="123456789",
                                                    start_of_support=date(2022, 1, 1),
                                                    level_of_needs=12,
                                                    nature_package=12)

        patient_list = [self.patient_john, self.patient_david, self.patient_lucy]

        # Call the create_monthly_invoice method
        statement = create_monthly_invoice(patient_list, self.month, self.year)

        # Check that a LongTermCareMonthlyStatement was created for the correct month and year
        self.assertEqual(statement.month, self.month)
        self.assertEqual(statement.year, self.year)

        # Check that a LongTermCareInvoiceFile was created for the patient and period
        invoice = LongTermCareInvoiceFile.objects.get(patient=self.patient_john,
                                                      invoice_start_period=date(2023, 4, 1),
                                                      invoice_end_period=date(2023, 4, 30))

        # Check that a LongTermCareInvoiceLine was created for the invoice and period
        # line = LongTermCareInvoiceLine.objects.get(invoice=invoice,
        #                                            start_period=date(2023, 4, 1),
        #                                            end_period=date(2023, 4, 30))
        self.assertEqual(statement.calculate_total_price(), Decimal('0'))
        # self.assertEqual(line.calculate_price(), Decimal('1723.47'))

        # Check that the LongTermCarePackage on the invoice line matches the level of needs from the medical care summary
        # self.assertEqual(line.long_term_care_package.dependence_level, 1)

    def test_against_activity_details(self):
        # Create a medical care summary for the patient
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_john,
                                                    date_of_decision=date(2022, 1, 10),
                                                    date_of_evaluation=date(2022, 1, 1),
                                                    date_of_request=date(2021, 12, 1),
                                                    date_of_notification=date(2022, 1, 11),
                                                    date_of_notification_to_provider=date(2022, 1, 12),
                                                    plan_number="123456789",
                                                    decision_number="123456789",
                                                    start_of_support=date(2022, 1, 1),
                                                    level_of_needs=1,
                                                    nature_package=1)
        long_term_monthly_activity = LongTermMonthlyActivity.objects.create(month=4, year=2023,
                                                                            patient=self.patient_john)
        LongTermMonthlyActivityDetail.objects.create(long_term_monthly_activity=long_term_monthly_activity,
                                                     activity_date=date(2023, 4, 1),
                                                     activity=LongTermCareItem.objects.get(code="AEVH01"),
                                                     quantity=5)
        LongTermMonthlyActivityDetail.objects.create(long_term_monthly_activity=long_term_monthly_activity,
                                                     activity_date=date(2023, 4, 2),
                                                     activity=LongTermCareItem.objects.get(code="AEVH01"),
                                                     quantity=5)
        patient_list = [self.patient_john]
        # Call the create_monthly_invoice method
        statement = create_monthly_invoice(patient_list, self.month, self.year)
        # Check that a LongTermCareInvoiceFile was created for the patient and period
        invoice = LongTermCareInvoiceFile.objects.get(patient=self.patient_john,
                                                      invoice_start_period=date(2023, 4, 1),
                                                      invoice_end_period=date(2023, 4, 30))
        self.assertEqual(invoice.calculate_price(), Decimal('118.86'))
        self.assertEqual(statement.calculate_total_price(), Decimal('118.86'))
        # now lets add a second activity cleaning
        LongTermMonthlyActivityDetail.objects.create(long_term_monthly_activity=long_term_monthly_activity,
                                                        activity_date=date(2023, 4, 1),
                                                        activity=LongTermCareItem.objects.get(code="AMD-M"),
                                                        quantity=3)
        # Call the create_monthly_invoice method
        statement = create_monthly_invoice(patient_list, self.month, self.year)
        self.assertEqual(invoice.calculate_price(), Decimal('172.34'))
        self.assertEqual(statement.calculate_total_price(), Decimal('172.34'))
    def test_patient_with_palliative_package(self):
        # Create a medical care summary for the patient
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_john,
                                                    date_of_decision=date(2022, 1, 10),
                                                    date_of_evaluation=date(2022, 1, 1),
                                                    date_of_request=date(2021, 12, 1),
                                                    date_of_notification=date(2022, 1, 11),
                                                    date_of_notification_to_provider=date(2022, 1, 12),
                                                    plan_number="123456789",
                                                    decision_number="123456789",
                                                    start_of_support=date(2022, 1, 1),
                                                    level_of_needs=1,
                                                    nature_package=1,
                                                    date_of_change_to_new_plan=date(2023, 4, 14))
        # create summary for palliative care
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_john,
                                                    date_of_decision=date(2023, 4, 15),
                                                    date_of_evaluation=date(2023, 4, 8),
                                                    date_of_request=date(2023, 4, 8),
                                                    date_of_notification=date(2023, 4, 15),
                                                    date_of_notification_to_provider=date(2023, 4, 15),
                                                    plan_number="123456789",
                                                    decision_number="123456789",
                                                    start_of_support=date(2022, 1, 1),
                                                    level_of_needs=780,
                                                    special_package="AEVFSP",
                                                    nature_package=None)
        long_term_monthly_activity = LongTermMonthlyActivity.objects.create(month=4, year=2023,
                                                                            patient=self.patient_john)
        # create LongTermMonthlyActivityDetail for every day of the month of April 2023
        for day in range(1, 31):
            LongTermMonthlyActivityDetail.objects.create(long_term_monthly_activity=long_term_monthly_activity,
                                                         activity_date=date(2023, 4, day),
                                                         activity=LongTermCareItem.objects.get(code="AEVH01"),
                                                         quantity=5)
        patient_list = [self.patient_john]
        # Call the create_monthly_invoice method
        statement = create_monthly_invoice(patient_list, self.month, self.year)
        # Check that a LongTermCareInvoiceFile was created for the patient and period
        invoice = LongTermCareInvoiceFile.objects.get(patient=self.patient_john,
                                                      invoice_start_period=date(2023, 4, 1),
                                                      invoice_end_period=date(2023, 4, 30))
        self.assertEqual(invoice.calculate_price(), Decimal('3480.66'))
        self.assertEqual(statement.calculate_total_price(), Decimal('3480.66'))
        # now lets add a second activity cleaning
        LongTermMonthlyActivityDetail.objects.create(long_term_monthly_activity=long_term_monthly_activity,
                                                        activity_date=date(2023, 4, 1),
                                                        activity=LongTermCareItem.objects.get(code="AMD-M"),
                                                        quantity=3)
        # Call the create_monthly_invoice method
        statement = create_monthly_invoice(patient_list, self.month, self.year)
        self.assertEqual(invoice.calculate_price(), Decimal('4282.86'))
        self.assertEqual(statement.calculate_total_price(), Decimal('4282.86'))

    def test_patient_all_days_of_month(self):
        # Create a medical care summary for the patient
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_john,
                                                    date_of_decision=date(2022, 1, 10),
                                                    date_of_evaluation=date(2022, 1, 1),
                                                    date_of_request=date(2021, 12, 1),
                                                    date_of_notification=date(2022, 1, 11),
                                                    date_of_notification_to_provider=date(2022, 1, 12),
                                                    plan_number="123456789",
                                                    decision_number="123456789",
                                                    start_of_support=date(2022, 1, 1),
                                                    level_of_needs=1,
                                                    nature_package=1)
        long_term_monthly_activity = LongTermMonthlyActivity.objects.create(month=4, year=2023,
                                                                            patient=self.patient_john)
        # create LongTermMonthlyActivityDetail for every day of the month of April 2023
        for day in range(1, 31):
            LongTermMonthlyActivityDetail.objects.create(long_term_monthly_activity=long_term_monthly_activity,
                                                         activity_date=date(2023, 4, day),
                                                         activity=LongTermCareItem.objects.get(code="AEVH01"),
                                                         quantity=5)
        patient_list = [self.patient_john]
        # Call the create_monthly_invoice method
        statement = create_monthly_invoice(patient_list, self.month, self.year)
        # Check that a LongTermCareInvoiceFile was created for the patient and period
        invoice = LongTermCareInvoiceFile.objects.get(patient=self.patient_john,
                                                      invoice_start_period=date(2023, 4, 1),
                                                      invoice_end_period=date(2023, 4, 30))
        self.assertEqual(invoice.calculate_price(), Decimal('1782.90'))
        self.assertEqual(statement.calculate_total_price(), Decimal('1782.90'))

