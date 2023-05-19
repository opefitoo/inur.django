from datetime import date

from django.test import TestCase

from dependence.detailedcareplan import MedicalCareSummaryPerPatient, get_summaries_between_two_dates
from invoices.models import Patient


class MedicalSummaryTest(TestCase):
    def setUp(self) -> None:
        self.patient_john = Patient.objects.create(id=1309, name="John", is_under_dependence_insurance=True,
                                                   date_of_exit=None)

    def test_get_summaries_between_two_dates(self):
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
        summaries = get_summaries_between_two_dates(self.patient_john,
                                                    start_date=date(2023, 1, 1),
                                                    end_date=date(2023, 1, 31))
        self.assertEqual(len(summaries), 1)
