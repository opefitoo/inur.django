from api.tests.views.base import BaseTestCase
from rest_framework.test import APITestCase

from api.serializers import PhysicianSerializer
from invoices.models import Physician


class PhysicianTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(PhysicianTestCase, self).setUp()
        self.model_name = 'physician'
        self.model = Physician
        self.serializer = PhysicianSerializer
        self.items = [self.model.objects.create(provider_code='provider_code0',
                                                first_name='first name 0',
                                                name='name 0',
                                                address='address 0',
                                                zipcode='zipcode 0',
                                                city='city 0',
                                                phone_number='000'),
                      self.model.objects.create(provider_code='provider_code1',
                                                first_name='first name 1',
                                                name='name 1',
                                                address='address 1',
                                                zipcode='zipcode 1',
                                                city='city 1',
                                                phone_number='111'),
                      self.model.objects.create(provider_code='provider_code2',
                                                first_name='first name 2',
                                                name='name 2',
                                                address='address 2',
                                                zipcode='zipcode 2',
                                                city='city 2',
                                                phone_number='222'),
                      self.model.objects.create(provider_code='provider_code3',
                                                first_name='first name 3',
                                                name='name 3',
                                                address='address 3',
                                                zipcode='zipcode 3',
                                                city='city 3',
                                                phone_number='333')]

        self.valid_payload = {
            'provider_code': 'provider_code5',
            'first_name': 'first_name 5',
            'name': 'Code5',
            'address': 'address 5',
            'zipcode': 'zipcode 5',
            'city': 'city 5',
            'phone_number': '555'
        }

        self.invalid_payload = {
            'name': 'name 6',
            'first_name': 'first_name 6',
        }
