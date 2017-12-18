from api.tests.views.base import BaseTestCase
from django.utils import timezone

from rest_framework.test import APITestCase

from api.serializers import HospitalizationSerializer
from invoices.models import Patient, Hospitalization


class HospitalizationTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(HospitalizationTestCase, self).setUp()
        self.model_name = 'hospitalization'
        self.model = Hospitalization
        self.serializer = HospitalizationSerializer

        date = timezone.now()
        self.start_date = date.replace(month=2, day=1)
        self.end_date = date.replace(month=3, day=1)

        patient = Patient.objects.create(code_sn='code_sn0',
                                         first_name='first name 0',
                                         name='name 0',
                                         address='address 0',
                                         zipcode='zipcode 0',
                                         city='city 0',
                                         phone_number='000')

        self.items = [self.model.objects.create(start_date=self.start_date,
                                                patient=patient,
                                                end_date=self.end_date),
                      self.model.objects.create(start_date=self.start_date.replace(month=4),
                                                patient=patient,
                                                end_date=self.end_date.replace(month=5)),
                      self.model.objects.create(start_date=self.start_date.replace(month=6),
                                                patient=patient,
                                                end_date=date.replace(month=7)),
                      self.model.objects.create(start_date=self.start_date.replace(month=8),
                                                patient=patient,
                                                end_date=self.end_date.replace(month=9))]

        self.valid_payload = {
            'start_date': self.start_date.replace(month=10).strftime('%Y-%m-%d'),
            'patient': patient.id,
            'end_date': self.end_date.replace(month=11).strftime('%Y-%m-%d')
        }

        self.invalid_payload = {
            'patient': '',
            'start_date': self.start_date.strftime('%Y-%m-%d')
        }
