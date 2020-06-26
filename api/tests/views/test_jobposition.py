from api.tests.views.base import BaseTestCase
from rest_framework.test import APITestCase

from api.serializers import JobPositionSerializer
from invoices.employee import JobPosition


class JobPositionTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(JobPositionTestCase, self).setUp()
        self.model_name = 'jobposition'
        self.model = JobPosition
        self.serializer = JobPositionSerializer
        self.items = [self.model.objects.create(name='Some name0'),
                      self.model.objects.create(name='Some name1'),
                      self.model.objects.create(name='Some name2'),
                      self.model.objects.create(name='Some name3')]

        self.valid_payload = {
            'name': 'Some name4'
        }

        self.invalid_payload = {
            'name': ''
        }
