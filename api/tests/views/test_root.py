from api.tests.views.base import BaseAuth

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


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