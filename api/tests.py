import json
import unittest

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase, APIRequestFactory, APIClient

from api.serializers import CareCodeSerializer, PatientSerializer
from invoices.models import CareCode, Patient


class BaseAuth(object):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = User.objects.create_user('testuser', email='testuser@test.com', password='testing')
        self.user.save()
        self.token = Token.objects.create(user=self.user)
        self.token.save()

    def _require_login(self):
        self.client.login(username='testuser', password='testing')
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)


class BaseTestCase(BaseAuth):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.client = APIClient()
        self.user = User.objects.create_user('testuser', email='testuser@test.com', password='testing')
        self.user.save()
        self.token = Token.objects.create(user=self.user)
        self.token.save()

    def _require_login(self):
        self.client.login(username='testuser', password='testing')
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_get_all(self):
        care_codes = self.model.objects.all()
        serializer = self.serializer(care_codes, many=True)

        self._require_login()
        url = reverse('api:' + self.model_name + '-list')
        response = self.client.get(url)

        self.assertEqual(response.data['results'], serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_get_valid_single(self):
        care_code = self.model.objects.get(pk=self.items[2].id)
        serializer = self.serializer(care_code)

        self._require_login()
        url = reverse('api:' + self.model_name + '-detail', kwargs={'pk': self.items[2].id})
        response = self.client.get(url)

        self.assertEqual(response.data, serializer.data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_valid(self):
        self._require_login()
        url = reverse('api:' + self.model_name + '-list')

        response = self.client.post(url, data=json.dumps(self.valid_payload), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_invalid(self):
        self._require_login()
        url = reverse('api:' + self.model_name + '-list')

        response = self.client.post(url, data=json.dumps(self.invalid_payload), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_update(self):
        self._require_login()
        url = reverse('api:' + self.model_name + '-detail', kwargs={'pk': self.items[2].id})

        response = self.client.put(url, data=json.dumps(self.valid_payload), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_invalid_update(self):
        self._require_login()
        url = reverse('api:' + self.model_name + '-detail', kwargs={'pk': self.items[2].id})

        response = self.client.put(url, data=json.dumps(self.invalid_payload), content_type='application/json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_delete(self):
        self._require_login()
        url = reverse('api:' + self.model_name + '-detail', kwargs={'pk': self.items[2].id})

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_invalid_delete(self):
        self._require_login()
        url = reverse('api:' + self.model_name + '-detail', kwargs={'pk': 600})

        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class RootTestCase(BaseAuth, APITestCase):
    def test_unauthenticated_root(self):
        url = reverse('api:api-root')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_authenticated_root(self):
        self._require_login()
        url = reverse('api:api-root')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class CareCodeTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(CareCodeTestCase, self).setUp()
        self.model_name = 'carecode'
        self.model = CareCode
        self.serializer = CareCodeSerializer
        self.items = [self.model.objects.create(code='Code1',
                                                name='Some name1',
                                                description='Description',
                                                gross_amount=10.2,
                                                reimbursed=False),
                      self.model.objects.create(code='Code2',
                                                name='Some name2',
                                                description='Description2',
                                                gross_amount=14.7,
                                                reimbursed=True),
                      self.model.objects.create(code='Code3',
                                                name='Some name3',
                                                description='Description3',
                                                gross_amount=2.1,
                                                reimbursed=False),
                      self.model.objects.create(code='Code4',
                                                name='Some name4',
                                                description='Description4',
                                                gross_amount=150.9,
                                                reimbursed=True)]

        self.valid_payload = {
            'code': 5,
            'name': 'Code5',
            'description': 'Description5',
            'gross_amount': 102.1
        }

        self.invalid_payload = {
            'name': 'Code6',
            'description': 'Description6',
            'gross_amount': 0.1
        }


class PatientTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(PatientTestCase, self).setUp()
        self.model_name = 'patient'
        self.model = Patient
        self.serializer = PatientSerializer
        self.items = [self.model.objects.create(code_sn='code_sn0',
                                                first_name='first name 0',
                                                name='name 0',
                                                address='address 0',
                                                zipcode='zipcode 0',
                                                city='city 0',
                                                phone_number='000'),
                      self.model.objects.create(code_sn='code_sn1',
                                                first_name='first name 1',
                                                name='name 1',
                                                address='address 1',
                                                zipcode='zipcode 1',
                                                city='city 1',
                                                phone_number='111'),
                      self.model.objects.create(code_sn='code_sn2',
                                                first_name='first name 2',
                                                name='name 2',
                                                address='address 2',
                                                zipcode='zipcode 2',
                                                city='city 2',
                                                phone_number='222'),
                      self.model.objects.create(code_sn='code_sn3',
                                                first_name='first name 3',
                                                name='name 3',
                                                address='address 3',
                                                zipcode='zipcode 3',
                                                city='city 3',
                                                phone_number='333')]

        self.valid_payload = {
            'code_sn': 'code_sn5',
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
