from api.tests.views.base import BaseTestCase
from django.utils import timezone
from rest_framework.test import APITestCase
from constance import config

from api.serializers import PrestationSerializer
from invoices.models import CareCode, Patient, InvoiceItem, Prestation


class PrestationTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(PrestationTestCase, self).setUp()
        self.model_name = 'prestation'
        self.model = Prestation
        self.serializer = PrestationSerializer

        date = timezone.now()
        # carecode = CareCode.objects.create(code=config.AT_HOME_CARE_CODE,
        #                                    name='Some name1',
        #                                    description='Description',
        #                                    reimbursed=False)
        patient = Patient.objects.create(code_sn='code_sn0',
                                         first_name='first name 0',
                                         name='name 0',
                                         address='address 0',
                                         zipcode='zipcode 0',
                                         city='city 0',
                                         phone_number='000')
        carecode = CareCode.objects.create(code='Code1',
                                           name='Some name1',
                                           description='Description',
                                           reimbursed=False)
        invoiceitem = InvoiceItem.objects.create(invoice_number='invoice_number0',
                                                 patient=patient,
                                                 invoice_date=date,
                                                 is_private=False)

        self.items = [self.model.objects.create(invoice_item=invoiceitem,
                                                carecode=carecode,
                                                date=date),
                      self.model.objects.create(invoice_item=invoiceitem,
                                                carecode=carecode,
                                                date=date),
                      self.model.objects.create(invoice_item=invoiceitem,
                                                carecode=carecode,
                                                date=date),
                      self.model.objects.create(invoice_item=invoiceitem,
                                                carecode=carecode,
                                                date=date)]

        self.valid_payload = {
            'invoice_item': invoiceitem.id,
            'carecode': carecode.id,
            'date': date.strftime('%Y-%m-%dT%H:%M:%S')
        }

        self.invalid_payload = {
            'invoice_item': 'invoice_item',
            'date': 'first_name 6',
        }
