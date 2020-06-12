import json

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory, APIClient


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

        self.assertEqual(response.data['count'], len(serializer.data))
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
