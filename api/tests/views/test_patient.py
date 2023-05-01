from rest_framework.test import APITestCase

from api.serializers import PatientSerializer
from api.tests.views.base import BaseTestCase
from invoices.models import Patient


class PatientTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(PatientTestCase, self).setUp()
        self.model_name = 'patient'
        self.model = Patient
        self.serializer = PatientSerializer
        self.items = [self.model.objects.create(code_sn='1977030661534',
                                                first_name='first name 0',
                                                name='name 0',
                                                address='address 0',
                                                zipcode='zipcode 0',
                                                city='city 0',
                                                country='LU',
                                                phone_number='000',
                                                participation_statutaire=True,
                                                is_under_dependence_insurance=True,
                                                is_private=False),
                      self.model.objects.create(code_sn='1961030661534',
                                                first_name='first name 1',
                                                name='name 1',
                                                address='address 1',
                                                zipcode='zipcode 1',
                                                city='city 1',
                                                country='LU',
                                                phone_number='111',
                                                participation_statutaire=True,
                                                is_under_dependence_insurance=True,
                                                is_private=False),
                      self.model.objects.create(code_sn='1983030661534',
                                                first_name='first name 2',
                                                name='name 2',
                                                address='address 2',
                                                zipcode='zipcode 2',
                                                city='city 2',
                                                country='LU',
                                                phone_number='222',
                                                participation_statutaire=True,
                                                is_under_dependence_insurance=True,
                                                is_private=False),
                      self.model.objects.create(code_sn='1970030661534',
                                                first_name='first name 3',
                                                name='name 3',
                                                address='address 3',
                                                zipcode='1999',
                                                city='city 3',
                                                country='LU',
                                                phone_number='333',
                                                participation_statutaire=True,
                                                is_under_dependence_insurance=True,
                                                is_private=False)]

        self.valid_payload = {
            'code_sn': '1966020661534',
            'first_name': 'Trotro',
            'name': 'BOURRICOT',
            'address': '27 Rue Plaine',
            'zipcode': '1200',
            'city': 'TAIPEI',
            'country':  {'code': 'AU', 'name': 'Australia'},
            'phone_number': '1111',
            'participation_statutaire': True,
            'is_private':  False,
        }

        self.invalid_payload = {
            'name': 'name 6',
            'first_name': 'first_name 6',
        }
