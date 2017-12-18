import json
from datetime import datetime
from django.utils import timezone

from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase, APIRequestFactory, APIClient
from constance import config

from api.serializers import CareCodeSerializer, PatientSerializer, PhysicianSerializer, InvoiceItemSerializer, \
    PrestationSerializer, JobPositionSerializer, TimesheetTaskSerializer, TimesheetSerializer, \
    MedicalPrescriptionSerializer, HospitalizationSerializer
from invoices.models import CareCode, Patient, Physician, InvoiceItem, Prestation, MedicalPrescription, Hospitalization
from invoices.timesheet import JobPosition, TimesheetTask, Timesheet, Employee


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


class PatientTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(PatientTestCase, self).setUp()
        self.model_name = 'patient'
        self.model = Patient
        self.serializer = PatientSerializer
        self.items = [self.model.objects.create(code_sn='1245789764822',
                                                first_name='first name 0',
                                                name='name 0',
                                                address='address 0',
                                                zipcode='zipcode 0',
                                                city='city 0',
                                                phone_number='000'),
                      self.model.objects.create(code_sn='2245789764822',
                                                first_name='first name 1',
                                                name='name 1',
                                                address='address 1',
                                                zipcode='zipcode 1',
                                                city='city 1',
                                                phone_number='111'),
                      self.model.objects.create(code_sn='3245789764822',
                                                first_name='first name 2',
                                                name='name 2',
                                                address='address 2',
                                                zipcode='zipcode 2',
                                                city='city 2',
                                                phone_number='222'),
                      self.model.objects.create(code_sn='4245789764822',
                                                first_name='first name 3',
                                                name='name 3',
                                                address='address 3',
                                                zipcode='zipcode 3',
                                                city='city 3',
                                                phone_number='333')]

        self.valid_payload = {
            'code_sn': '5245789764822',
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


class PhysicianTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(PhysicianTestCase, self).setUp()
        self.model_name = 'physician'
        self.model = Physician
        self.serializer = PhysicianSerializer
        self.items = [self.model.objects.create(provider_code='provider_code0',
                                                first_name='first name 0',
                                                name='name 0',
                                                address='address 0',
                                                zipcode='zipcode 0',
                                                city='city 0',
                                                phone_number='000'),
                      self.model.objects.create(provider_code='provider_code1',
                                                first_name='first name 1',
                                                name='name 1',
                                                address='address 1',
                                                zipcode='zipcode 1',
                                                city='city 1',
                                                phone_number='111'),
                      self.model.objects.create(provider_code='provider_code2',
                                                first_name='first name 2',
                                                name='name 2',
                                                address='address 2',
                                                zipcode='zipcode 2',
                                                city='city 2',
                                                phone_number='222'),
                      self.model.objects.create(provider_code='provider_code3',
                                                first_name='first name 3',
                                                name='name 3',
                                                address='address 3',
                                                zipcode='zipcode 3',
                                                city='city 3',
                                                phone_number='333')]

        self.valid_payload = {
            'provider_code': 'provider_code5',
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


class PrestationTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(PrestationTestCase, self).setUp()
        self.model_name = 'prestation'
        self.model = Prestation
        self.serializer = PrestationSerializer

        date = timezone.now()
        carecode = CareCode.objects.create(code=config.AT_HOME_CARE_CODE,
                                           name='Some name1',
                                           description='Description',
                                           reimbursed=False)
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


class TimesheetTaskTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(TimesheetTaskTestCase, self).setUp()
        self.model_name = 'timesheettask'
        self.model = TimesheetTask
        self.serializer = TimesheetTaskSerializer
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


class TimesheetTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(TimesheetTestCase, self).setUp()
        self.model_name = 'timesheet'
        self.model = Timesheet
        self.serializer = TimesheetSerializer

        date = datetime.now()
        jobposition = JobPosition.objects.create(name='name 0')
        employee = Employee.objects.create(user=self.user,
                                           start_contract=date,
                                           occupation=jobposition)

        self.items = [self.model.objects.create(start_date=date,
                                                employee=employee,
                                                end_date=date),
                      self.model.objects.create(start_date=date,
                                                employee=employee,
                                                end_date=date),
                      self.model.objects.create(start_date=date,
                                                employee=employee,
                                                end_date=date),

                      self.model.objects.create(start_date=date,
                                                employee=employee,
                                                end_date=date)]

        self.valid_payload = {
            'start_date': date.strftime('%Y-%m-%d'),
            'employee': employee.id,
            'end_date': date.strftime('%Y-%m-%d')
        }

        self.invalid_payload = {
            'employee': '',
            'start_date': date.strftime('%Y-%m-%d')
        }


class MedicalPrescriptionTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(MedicalPrescriptionTestCase, self).setUp()
        date = datetime.now().replace(month=2, day=1)
        end_date = datetime.now().replace(month=3, day=1)

        patient = Patient.objects.create(code_sn='code_sn0',
                                         first_name='first name 0',
                                         name='name 0',
                                         address='address 0',
                                         zipcode='zipcode 0',
                                         city='city 0',
                                         phone_number='000')

        physician = Physician.objects.create(provider_code='provider_code0',
                                             first_name='first name 0',
                                             name='name 0',
                                             address='address 0',
                                             zipcode='zipcode 0',
                                             city='city 0',
                                             phone_number='000')

        self.model_name = 'medicalprescription'
        self.model = MedicalPrescription
        self.serializer = MedicalPrescriptionSerializer
        self.items = [self.model.objects.create(prescriptor=physician,
                                                patient=patient,
                                                date=date.strftime('%Y-%m-%d'),
                                                end_date=end_date.strftime('%Y-%m-%d')),
                      self.model.objects.create(prescriptor=physician,
                                                patient=patient,
                                                date=date.strftime('%Y-%m-%d'),
                                                end_date=end_date.strftime('%Y-%m-%d')),
                      self.model.objects.create(prescriptor=physician,
                                                patient=patient,
                                                date=date.strftime('%Y-%m-%d'),
                                                end_date=end_date.strftime('%Y-%m-%d')),
                      self.model.objects.create(prescriptor=physician,
                                                patient=patient,
                                                date=date.strftime('%Y-%m-%d'),
                                                end_date=end_date.strftime('%Y-%m-%d'))]

        self.valid_payload = {
            'prescriptor': physician.id,
            'patient': patient.id,
            'date': date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
        }

        self.invalid_payload = {
            'date': date.strftime('%Y-%m-%d')
        }


class HospitalizationTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(HospitalizationTestCase, self).setUp()
        self.model_name = 'hospitalization'
        self.model = Hospitalization
        self.serializer = HospitalizationSerializer

        date = timezone.now()
        self.start_date = date.replace(month=2, day=1)
        self.end_date = date.replace(month=3, day=1)

        patient = Patient.objects.create(code_sn='code_sn0',
                                         first_name='first name 0',
                                         name='name 0',
                                         address='address 0',
                                         zipcode='zipcode 0',
                                         city='city 0',
                                         phone_number='000')

        self.items = [self.model.objects.create(start_date=self.start_date,
                                                patient=patient,
                                                end_date=self.end_date),
                      self.model.objects.create(start_date=self.start_date.replace(month=4),
                                                patient=patient,
                                                end_date=self.end_date.replace(month=5)),
                      self.model.objects.create(start_date=self.start_date.replace(month=6),
                                                patient=patient,
                                                end_date=date.replace(month=7)),
                      self.model.objects.create(start_date=self.start_date.replace(month=8),
                                                patient=patient,
                                                end_date=self.end_date.replace(month=9))]

        self.valid_payload = {
            'start_date': self.start_date.replace(month=10).strftime('%Y-%m-%d'),
            'patient': patient.id,
            'end_date': self.end_date.replace(month=11).strftime('%Y-%m-%d')
        }

        self.invalid_payload = {
            'patient': '',
            'start_date': self.start_date.strftime('%Y-%m-%d')
        }
