from django.utils import timezone
from django.utils.datetime_safe import datetime
from rest_framework.test import APITestCase

from api.serializers import PrestationSerializer
from api.tests.views.base import BaseTestCase
from invoices.employee import Employee, JobPosition
from invoices.models import CareCode, Patient, InvoiceItem, Prestation
from invoices.modelspackage import InvoicingDetails


class PrestationTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(PrestationTestCase, self).setUp()
        self.model_name = 'prestation'
        self.model = Prestation
        self.serializer = PrestationSerializer
        date = datetime.now()
        jobposition = JobPosition.objects.create(name='name 0')
        employee = Employee.objects.create(user=self.user,
                                           start_contract=date,
                                           occupation=jobposition)
        invoicing_dtls = InvoicingDetails.objects.create(
            provider_code="111111",
            name="BEST.lu",
            address="Sesame Street",
            zipcode_city="1234 Sesame Street",
            bank_account="LU12 3456 7890 1234 5678")

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
                                                 invoice_details=invoicing_dtls,
                                                 is_private=False)

        self.items = [self.model.objects.create(invoice_item=invoiceitem,
                                                carecode=carecode,
                                                employee=employee,
                                                date=date),
                      self.model.objects.create(invoice_item=invoiceitem,
                                                carecode=carecode,
                                                employee=employee,
                                                date=date),
                      self.model.objects.create(invoice_item=invoiceitem,
                                                carecode=carecode,
                                                employee=employee,
                                                date=date),
                      self.model.objects.create(invoice_item=invoiceitem,
                                                carecode=carecode,
                                                employee=employee,
                                                date=date)]

        self.valid_payload = {
            'invoice_item': invoiceitem.id,
            'carecode': carecode.id,
            'employee': employee.id,
            'invoice_details': invoicing_dtls.id,
            'date': date.strftime('%Y-%m-%dT%H:%M:%S')
        }

        self.invalid_payload = {
            'invoice_item': 'invoice_item',
            'date': 'first_name 6',
        }
