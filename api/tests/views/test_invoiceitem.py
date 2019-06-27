from datetime import datetime

from api.tests.views.base import BaseTestCase
from rest_framework.test import APITestCase

from api.serializers import InvoiceItemSerializer
from invoices.models import Patient, InvoiceItem


class InvoiceItemTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(InvoiceItemTestCase, self).setUp()
        self.model_name = 'invoiceitem'
        self.model = InvoiceItem
        self.serializer = InvoiceItemSerializer

        date = datetime.now()
        patient = Patient.objects.create(code_sn='code_sn0',
                                         first_name='first name 0',
                                         name='name 0',
                                         address='address 0',
                                         zipcode='zipcode 0',
                                         city='city 0',
                                         phone_number='000')

        self.items = [self.model.objects.create(invoice_number='invoice_number0',
                                                patient=patient,
                                                invoice_date=date,
                                                is_private=False),
                      self.model.objects.create(invoice_number='invoice_number1',
                                                patient=patient,
                                                invoice_date=date,
                                                is_private=False),
                      self.model.objects.create(invoice_number='invoice_number2',
                                                patient=patient,
                                                invoice_date=date,
                                                is_private=False),
                      self.model.objects.create(invoice_number='invoice_number3',
                                                patient=patient,
                                                invoice_date=date,
                                                is_private=False)]

        self.valid_payload = {
            'invoice_number': 'invoice_number4',
            'patient': patient.id,
            'prestations': [],
            'invoice_date': date.strftime('%Y-%m-%d'),
            'is_private': False
        }

        self.invalid_payload = {
            'invoice_number': '',
            'invoice_date': date.strftime('%Y-%m-%d')
        }
