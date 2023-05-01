import os

from django.test import TestCase
from django.utils import timezone

from invoices.models import Physician, MedicalPrescription, Patient, update_medical_prescription_filename
from invoices.storages import CustomizedGoogleDriveStorage


class MedicalPrescriptionTestCase(TestCase):

    def test_autocomplete(self):
        self.assertEqual(MedicalPrescription.autocomplete_search_fields(),
                         ('date', 'prescriptor__name', 'prescriptor__first_name',
                          'patient__name',
                          'patient__first_name',
                          'prescriptor__provider_code'
                          ))

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

    def test_file_description(self):
        date = timezone.now()
        patient = Patient(first_name='first name',
                          name='name')
        prescription = MedicalPrescription(date=date,
                                           patient=patient)
        self.assertEqual(prescription.file_description, '%s %s %s' % (
            prescription.patient.name, prescription.patient.first_name, str(prescription.date)))


class UpdateMedicalPrescriptionFilenameTestCase(TestCase):
    def test_filename(self):
        filename = 'somename.jpg'
        date = timezone.now().date()
        patient = Patient(first_name='first name',
                          name='name')
        prescriptor = Physician(provider_code='1111', first_name='doc', name='toubib')
        prescription = MedicalPrescription(date=date,
                                           patient=patient, prescriptor=prescriptor)

        path = os.path.join(CustomizedGoogleDriveStorage.MEDICAL_PRESCRIPTION_FOLDER, str(prescription.date.year),
                            str(prescription.date.month))
        file_name, file_extension = os.path.splitext(filename)
        '%s_%s_%s%s' % (
            prescription.patient.name, prescription.patient.first_name, str(prescription.date), file_extension)
        filename = '%s_%s_%s_%s%s' % (prescription.prescriptor.name, prescription.patient.name,
                                           prescription.patient.first_name,
                                           str(prescription.date), file_extension)
        expected_name = os.path.join(path, filename)

        generated_name = update_medical_prescription_filename(prescription, filename)
        # because of uuid it's not possible to test the exact name
        self.assertTrue(os.path.splitext(generated_name)[0].startswith(os.path.splitext(expected_name)[0]))
