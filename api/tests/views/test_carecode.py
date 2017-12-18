from api.tests.views.base import BaseTestCase

from rest_framework.test import APITestCase

from api.serializers import CareCodeSerializer
from invoices.models import CareCode


class CareCodeTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(CareCodeTestCase, self).setUp()
        self.model_name = 'carecode'
        self.model = CareCode
        self.serializer = CareCodeSerializer
        self.items = [self.model.objects.create(code='Code1',
                                                name='Some name1',
                                                description='Description',
                                                reimbursed=False),
                      self.model.objects.create(code='Code2',
                                                name='Some name2',
                                                description='Description2',
                                                reimbursed=True),
                      self.model.objects.create(code='Code3',
                                                name='Some name3',
                                                description='Description3',
                                                reimbursed=False),
                      self.model.objects.create(code='Code4',
                                                name='Some name4',
                                                description='Description4',
                                                reimbursed=True)]

        self.valid_payload = {
            'code': 5,
            'name': 'Code5',
            'description': 'Description5'
        }

        self.invalid_payload = {
            'name': 'Code6',
            'description': 'Description6'
        }
