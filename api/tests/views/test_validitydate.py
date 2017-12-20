from api.tests.views.base import BaseTestCase
from django.utils import timezone

from rest_framework.test import APITestCase

from api.serializers import ValidityDateSerializer
from invoices.models import CareCode, ValidityDate


class ValidityDateTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(ValidityDateTestCase, self).setUp()
        self.model_name = 'validitydate'
        self.model = ValidityDate
        self.serializer = ValidityDateSerializer

        date = timezone.now()
        self.start_date = date.replace(month=2, day=1)
        self.end_date = date.replace(month=3, day=1)

        carecode = CareCode.objects.create(code='Code1',
                                           name='Some name1',
                                           description='Description',
                                           reimbursed=False)

        self.items = [self.model.objects.create(start_date=self.start_date,
                                                care_code=carecode,
                                                end_date=self.end_date,
                                                gross_amount=10.5),
                      self.model.objects.create(start_date=self.start_date.replace(month=4),
                                                care_code=carecode,
                                                end_date=self.end_date.replace(month=5),
                                                gross_amount=11.5),
                      self.model.objects.create(start_date=self.start_date.replace(month=6),
                                                care_code=carecode,
                                                end_date=date.replace(month=7),
                                                gross_amount=0.5),
                      self.model.objects.create(start_date=self.start_date.replace(month=8),
                                                care_code=carecode,
                                                end_date=self.end_date.replace(month=9),
                                                gross_amount=99.5)]

        self.valid_payload = {
            'start_date': self.start_date.replace(month=10).strftime('%Y-%m-%d'),
            'care_code': carecode.id,
            'gross_amount': 10.5,
            'end_date': self.end_date.replace(month=11).strftime('%Y-%m-%d')
        }

        self.invalid_payload = {
            'care_code': '',
            'start_date': self.start_date.strftime('%Y-%m-%d')
        }
