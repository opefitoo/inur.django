from datetime import datetime

from api.tests.views.base import BaseTestCase
from rest_framework.test import APITestCase

from api.serializers import MedicalPrescriptionSerializer
from invoices.models import Patient, Physician, MedicalPrescription


class MedicalPrescriptionTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(MedicalPrescriptionTestCase, self).setUp()
        date = datetime.now().replace(month=2, day=1)
        end_date = datetime.now().replace(month=3, day=1)

        patient = Patient.objects.create(code_sn='code_sn0',
                                         first_name='first name 0',
                                         name='name 0',
                                         address='address 0',
                                         zipcode='zipcode 0',
                                         city='city 0',
                                         phone_number='000')

        physician = Physician.objects.create(provider_code='provider_code0',
                                             first_name='first name 0',
                                             name='name 0',
                                             address='address 0',
                                             zipcode='zipcode 0',
                                             city='city 0',
                                             phone_number='000')

        self.model_name = 'medicalprescription'
        self.model = MedicalPrescription
        self.serializer = MedicalPrescriptionSerializer
        self.items = [self.model.objects.create(prescriptor=physician,
                                                patient=patient,
                                                date=date.strftime('%Y-%m-%d'),
                                                end_date=end_date.strftime('%Y-%m-%d')),
                      self.model.objects.create(prescriptor=physician,
                                                patient=patient,
                                                date=date.strftime('%Y-%m-%d'),
                                                end_date=end_date.strftime('%Y-%m-%d')),
                      self.model.objects.create(prescriptor=physician,
                                                patient=patient,
                                                date=date.strftime('%Y-%m-%d'),
                                                end_date=end_date.strftime('%Y-%m-%d')),
                      self.model.objects.create(prescriptor=physician,
                                                patient=patient,
                                                date=date.strftime('%Y-%m-%d'),
                                                end_date=end_date.strftime('%Y-%m-%d'))]

        self.valid_payload = {
            'prescriptor': physician.id,
            'patient': patient.id,
            'date': date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
        }

        self.invalid_payload = {
            'date': date.strftime('%Y-%m-%d')
        }
