from datetime import datetime, date

from django.test import TestCase

from dependence.detailedcareplan import MedicalCareSummaryPerPatient, get_summaries_between_two_dates
from invoices.models import Patient


class TestMedicalCareSummary(TestCase):

    def setUp(self):
        Patient.objects.filter(id=3000).delete()
        self.patient_john = Patient.objects.create(id=3000, name="John", is_under_dependence_insurance=True,
                                                   date_of_exit=None)
        # Create a medical care summary for the patient
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_john,
                                                    date_of_decision=datetime(2022, 1, 10),
                                                    date_of_evaluation=datetime(2022, 1, 1),
                                                    date_of_request=datetime(2021, 12, 1),
                                                    date_of_notification=datetime(2022, 1, 11),
                                                    date_of_notification_to_provider=datetime(2022, 1, 12),
                                                    date_of_change_to_new_plan=datetime(2022, 12, 31),
                                                    plan_number="123456789",
                                                    decision_number="123456789",
                                                    start_of_support=datetime(2022, 1, 1),
                                                    level_of_needs=1,
                                                    nature_package=1)

        # Create a medical care summary for the patient
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_john,
                                                    date_of_decision=datetime(2023, 1, 1),
                                                    date_of_evaluation=datetime(2023, 1, 1),
                                                    date_of_request=datetime(2023, 12, 20),
                                                    date_of_notification=datetime(2023, 1, 5),
                                                    date_of_notification_to_provider=datetime(2023, 1, 5),
                                                    date_of_change_to_new_plan=datetime(2023, 1, 14),
                                                    plan_number="123456700",
                                                    decision_number="123456789",
                                                    start_of_support=datetime(2022, 1, 1),
                                                    level_of_needs=3,
                                                    nature_package=2)
        # Create a medical care summary for the patient
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_john,
                                                    date_of_decision=datetime(2023, 1, 15),
                                                    date_of_evaluation=datetime(2023, 1, 14),
                                                    date_of_request=datetime(2023, 1, 10),
                                                    date_of_notification=datetime(2023, 1, 17),
                                                    date_of_notification_to_provider=datetime(2023, 1, 17),
                                                    plan_number="123456700",
                                                    decision_number="123456789",
                                                    start_of_support=datetime(2022, 1, 1),
                                                    level_of_needs=8,
                                                    nature_package=4)

        Patient.objects.filter(id=4000).delete()
        self.patient_pete = Patient.objects.create(id=4000, name="Pete", is_under_dependence_insurance=True,
                                                   date_of_exit=None)
        # Create a medical care summary for the patient
        MedicalCareSummaryPerPatient.objects.create(patient=self.patient_pete,
                                                    date_of_decision=datetime(2022, 1, 10),
                                                    date_of_evaluation=datetime(2022, 1, 1),
                                                    date_of_request=datetime(2021, 12, 1),
                                                    date_of_notification=datetime(2022, 1, 11),
                                                    date_of_notification_to_provider=datetime(2022, 1, 12),
                                                    plan_number="123456789",
                                                    decision_number="123456789",
                                                    start_of_support=datetime(2022, 1, 1),
                                                    level_of_needs=1,
                                                    nature_package=1)

    def test_get_summaries_between_two_dates_only_one(self):
        """
        Test that a medical care summary is retrieved for a patient
        @return: None
        """
        summaries = get_summaries_between_two_dates(self.patient_john, date(2022, 1, 1),
                                                    date(2022, 1, 31))
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].medicalSummaryPerPatient.level_of_needs, 1)
        self.assertEqual(summaries[0].start_date, date(2022, 1, 10))
        self.assertEqual(summaries[0].end_date, date(2022, 12, 31))

    def test_get_summaries_between_two_dates_two(self):
        """
        Test that two medical care summaries are retrieved for a patient
        @return: None
        """
        summaries = get_summaries_between_two_dates(self.patient_john, date(2023, 1, 1),
                                                    date(2023, 1, 31))
        self.assertEqual(len(summaries), 2)
        self.assertEqual(summaries[0].medicalSummaryPerPatient.level_of_needs, 3)
        self.assertEqual(summaries[0].start_date, date(2023, 1, 1))
        self.assertEqual(summaries[0].end_date, date(2023, 1, 14))
        self.assertEqual(summaries[1].medicalSummaryPerPatient.level_of_needs, 8)
        self.assertEqual(summaries[1].start_date, date(2023, 1, 15))
        self.assertEqual(summaries[1].end_date, date(2023, 1, 31))

    def test_get_summaries_between_two_very_close_dates(self):
        """
        Test that two medical care summaries are retrieved for a patient
        @return: None
        """
        summaries = get_summaries_between_two_dates(self.patient_john, date(2023, 1, 1),
                                                    date(2023, 1, 2))
        self.assertEqual(len(summaries), 1)
        self.assertEqual(summaries[0].medicalSummaryPerPatient.level_of_needs, 3)
        self.assertEqual(summaries[0].start_date, date(2023, 1, 1))
        self.assertEqual(summaries[0].end_date, date(2023, 1, 2))
