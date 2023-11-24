from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory, APIClient


class AnotherBaseAuth(object):
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
