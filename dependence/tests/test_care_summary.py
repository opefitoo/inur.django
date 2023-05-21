from datetime import date

from django.test import TestCase

from dependence.detailedcareplan import MedicalCareSummaryPerPatient, get_summaries_between_two_dates
from invoices.models import Patient


class MedicalSummaryTest(TestCase):
    fixtures = ['test_data/medical_care_summary_per_patient.json']
    def setUp(self) -> None:
        self.patient_john = Patient.objects.create(id=1309, name="John", is_under_dependence_insurance=True,
                                                   date_of_exit=None)
        self.patient_dark_valor = Patient.objects.filter(id=1070).get()
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

    def test_forfait_soins_palliatifs(self):
        summaries = get_summaries_between_two_dates(self.patient_dark_valor,
                                                    start_date=date(2023, 3, 1),
                                                    end_date=date(2023, 3, 13))
        self.assertEqual(len(summaries), 2)
        self.assertEqual(summaries[1].start_date, date(2023, 3, 1))
        self.assertEqual(summaries[1].end_date, date(2023, 3, 10))
        self.assertEqual(summaries[1].medicalSummaryPerPatient.level_of_needs, 780)
        self.assertEqual(summaries[0].start_date, date(2023, 3, 11))
        self.assertEqual(summaries[0].end_date, date(2023, 3, 13))
        self.assertEqual(summaries[0].medicalSummaryPerPatient.level_of_needs, 1)
