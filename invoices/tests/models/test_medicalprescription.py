from django.utils import timezone
from django.test import TestCase

from invoices.models import Physician, MedicalPrescription


class MedicalPrescriptionTestCase(TestCase):
    def test_string_representation(self):
        date = timezone.now()
        physician = Physician(first_name='first name',
                              name='name')

        prescription = MedicalPrescription(prescriptor=physician,
                                           date=date)

        self.assertEqual(str(prescription),
                         '%s %s' % (prescription.prescriptor.name.strip(), prescription.prescriptor.first_name.strip()))

    def test_autocomplete(self):
        self.assertEqual(MedicalPrescription.autocomplete_search_fields(),
                         ('date', 'prescriptor__name', 'prescriptor__first_name'))

    def test_validate_dates(self):
        data = {
            'date': timezone.now().replace(month=1, day=10),
            'end_date': timezone.now().replace(month=6, day=10)
        }

        self.assertEqual(MedicalPrescription.validate_dates(data), {})

        data['date'] = data['date'].replace(month=6, day=10)
        self.assertEqual(MedicalPrescription.validate_dates(data), {})

        data['date'] = data['date'].replace(month=6, day=11)
        self.assertEqual(MedicalPrescription.validate_dates(data),
                         {'end_date': 'End date must be bigger than Start date'})
