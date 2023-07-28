from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from invoices.employee import Employee, JobPosition
from invoices.models import CareCode, Patient, Prestation, InvoiceItem, Hospitalization
from invoices.modelspackage import InvoicingDetails


class HospitalizationTestCase(TestCase):
    def setUp(self):
        self.start_date = timezone.now().replace(month=1, day=10)
        self.end_date = timezone.now().replace(month=6, day=10)

        user = User.objects.create_user('testuser', email='testuser@test.com', password='testing')
        user.save()
        jobposition = JobPosition.objects.create(name='name 0')
        self.employee = Employee.objects.create(user=user,
                                                start_contract=self.start_date,
                                                occupation=jobposition)

        self.patient = Patient.objects.create(code_sn='1245789764822',
                                              first_name='first name 0',
                                              name='name 0',
                                              address='address 0',
                                              zipcode='zipcode 0',
                                              city='city 0',
                                              phone_number='000')
        invoicing_dtls = InvoicingDetails.objects.create(
            provider_code="111111",
            name="BEST.lu",
            address="Sesame Street",
            zipcode_city="1234 Sesame Street",
            bank_account="LU12 3456 7890 1234 5678")

        self.invoice_item = InvoiceItem.objects.create(invoice_number='936 some invoice_number',
                                                       invoice_date=self.start_date,
                                                       invoice_details=invoicing_dtls,
                                                       patient=self.patient)

        self.care_code = CareCode.objects.create(code='code0',
                                                 name='some name',
                                                 description='description',
                                                 reimbursed=False)

        self.prestation = Prestation.objects.create(invoice_item=self.invoice_item,
                                                    employee=self.employee,
                                                    carecode=self.care_code,
                                                    date=self.start_date)

        self.hospitalization = Hospitalization.objects.create(start_date=self.start_date,
                                                              end_date=self.end_date,
                                                              patient=self.patient)

    def test_string_representation(self):
        hospitalization = Hospitalization(start_date=self.start_date,
                                          end_date=self.end_date,
                                          patient=self.patient)

        self.assertEqual(str(hospitalization), 'From %s to %s for %s' % (
            hospitalization.start_date, hospitalization.end_date, hospitalization.patient))

    def test_validate_dates(self):
        data = {
            'start_date': timezone.now().replace(month=1, day=10),
            'end_date': timezone.now().replace(month=6, day=10)
        }

        self.assertEqual(Hospitalization.validate_dates(data), {})

        data['start_date'] = data['start_date'].replace(month=6, day=10)
        self.assertEqual(Hospitalization.validate_dates(data), {})

        data['start_date'] = data['start_date'].replace(month=6, day=11)
        self.assertEqual(Hospitalization.validate_dates(data), {'end_date': 'End date must be bigger than Start date'})

    def test_validate_prestation(self):
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'patient': self.patient
        }
        error_msg = {'start_date': 'error 2807 Prestation(s) exist in selected dates range for this Patient'}
        self.assertEqual(Hospitalization.validate_prestation(data), error_msg)

        data['start_date'] = data['start_date'].replace(month=1, day=11)
        self.assertEqual(Hospitalization.validate_prestation(data), {})

        data['start_date'] = data['start_date'].replace(month=1, day=5)
        self.assertEqual(Hospitalization.validate_prestation(data), error_msg)

        data['patient'] = Patient.objects.create(code_sn='1245789764822',
                                                 first_name='first name 0',
                                                 name='name 0',
                                                 address='address 0',
                                                 zipcode='zipcode 0',
                                                 city='city 0',
                                                 phone_number='000')

        self.assertEqual(Hospitalization.validate_prestation(data), {})

    def test_validate_date_range(self):
        data = {
            'start_date': self.start_date,
            'end_date': self.end_date,
            'patient': self.patient
        }
        error_msg = {'start_date': 'Intersection with other Hospitalizations'}

        self.assertEqual(Hospitalization.validate_date_range(self.hospitalization.id, data), {})
        self.assertEqual(Hospitalization.validate_date_range(None, data), error_msg)

        data['start_date'] = data['start_date'].replace(month=1, day=1)
        data['end_date'] = data['end_date'].replace(month=1, day=4)
        self.assertEqual(Hospitalization.validate_date_range(None, data), {})

        data['end_date'] = data['end_date'].replace(month=1, day=10)
        self.assertEqual(Hospitalization.validate_date_range(None, data), error_msg)

        data['end_date'] = data['end_date'].replace(month=4)
        self.assertEqual(Hospitalization.validate_date_range(None, data), error_msg)

        data['start_date'] = data['start_date'].replace(month=3)
        data['end_date'] = data['end_date'].replace(month=5)
        self.assertEqual(Hospitalization.validate_date_range(None, data), error_msg)

        data['end_date'] = data['end_date'].replace(month=7)
        self.assertEqual(Hospitalization.validate_date_range(None, data), error_msg)

        data['start_date'] = data['start_date'].replace(month=6, day=10)
        self.assertEqual(Hospitalization.validate_date_range(None, data), error_msg)

        data['start_date'] = data['start_date'].replace(month=7)
        data['end_date'] = data['end_date'].replace(month=8)
        self.assertEqual(Hospitalization.validate_date_range(None, data), {})

    def test_validate_patient_alive(self):
        error_msg = {'end_date': "Hospitalization cannot be later than or include Patient's death date"}
        date_of_death = timezone.now().replace(month=6, day=10).date()
        data = {
            'patient': self.patient,
            'end_date': date_of_death
        }

        self.assertEqual(Hospitalization.validate_patient_alive(data), {})

        self.patient.date_of_death = date_of_death
        self.patient.save()

        self.assertEqual(Hospitalization.validate_patient_alive(data), {})

        data['end_date'] = data['end_date'].replace(month=8)
        self.assertEqual(Hospitalization.validate_patient_alive(data), error_msg)

        data['end_date'] = data['end_date'].replace(month=5)
        self.assertEqual(Hospitalization.validate_patient_alive(data), {})
