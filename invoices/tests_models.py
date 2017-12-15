from datetime import datetime
from django.utils import timezone
from django.test import TestCase
from django.contrib.auth.models import User

from invoices.models import CareCode, Patient, Physician, Prestation, InvoiceItem, get_default_invoice_number, \
    ValidityDate, MedicalPrescription, Hospitalization
from invoices.timesheet import Employee, JobPosition


class CareCodeTestCase(TestCase):
    def test_string_representation(self):
        carecode = CareCode(code='code',
                            name='some name',
                            description='description',
                            reimbursed=False)

        self.assertEqual(str(carecode), '%s: %s' % (carecode.code, carecode.name))

    def test_autocomplete(self):
        self.assertEqual(CareCode.autocomplete_search_fields(), ('name', 'code'))


class ValidityDateTestCase(TestCase):
    def setUp(self):
        self.care_code = CareCode.objects.create(code='code',
                                                 name='some name',
                                                 description='description',
                                                 reimbursed=False)

    def test_string_representation(self):
        date = datetime.now()
        validity_date = ValidityDate(start_date=date,
                                     gross_amount=10.5,
                                     care_code=self.care_code)

        self.assertEqual(str(validity_date), 'from %s to %s' % (validity_date.start_date, validity_date.end_date))

    def test_dates_validation(self):
        now = datetime.now()

        self.assertEqual(ValidityDate.check_dates(now.replace(month=1), now.replace(month=12)), True)
        self.assertEqual(ValidityDate.check_dates(now.replace(month=12), now.replace(month=1)), False)


class PatientTestCase(TestCase):
    def setUp(self):
        Patient.objects.create(code_sn='1245789764822',
                               first_name='first name 0',
                               name='name 0',
                               address='address 0',
                               zipcode='zipcode 0',
                               city='city 0',
                               phone_number='000'),

    def test_string_representation(self):
        patient = Patient(first_name='first name',
                          name='name')

        self.assertEqual(str(patient), '%s %s' % (patient.name.strip(), patient.first_name.strip()))

    def test_autocomplete(self):
        self.assertEqual(Patient.autocomplete_search_fields(), ('name', 'first_name'))

    def test_code_sn(self):
        is_code_sn_valid, message = Patient.is_code_sn_valid(None, is_private=True, code_sn='0123')
        self.assertEqual(is_code_sn_valid, True)

        is_code_sn_valid, message = Patient.is_code_sn_valid(None, is_private=False, code_sn='0123')
        self.assertEqual(is_code_sn_valid, False)

        is_code_sn_valid, message = Patient.is_code_sn_valid(None, is_private=False, code_sn='0245789764822')
        self.assertEqual(is_code_sn_valid, False)

        is_code_sn_valid, message = Patient.is_code_sn_valid(None, is_private=False, code_sn='1245789764822')
        self.assertEqual(is_code_sn_valid, False)

        is_code_sn_valid, message = Patient.is_code_sn_valid(None, is_private=False, code_sn='2245789764822')
        self.assertEqual(is_code_sn_valid, True)


class PhysicianTestCase(TestCase):
    def test_string_representation(self):
        physician = Physician(first_name='first name',
                              name='name')

        self.assertEqual(str(physician), '%s %s' % (physician.name.strip(), physician.first_name.strip()))

    def test_autocomplete(self):
        self.assertEqual(Physician.autocomplete_search_fields(), ('name', 'first_name'))


class MedicalPrescriptionTestCase(TestCase):
    def test_string_representation(self):
        date = timezone.now()
        physician = Physician(first_name='first name',
                              name='name')

        prescription = MedicalPrescription(prescriptor=physician,
                                           date=date)

        self.assertEqual(str(prescription),
                         '%s %s' % (prescription.prescriptor.name.strip(), prescription.prescriptor.first_name.strip()))

    def test_autocomplete(self):
        self.assertEqual(MedicalPrescription.autocomplete_search_fields(),
                         ('date', 'prescriptor__name', 'prescriptor__first_name'))


class PrestationTestCase(TestCase):
    def setUp(self):
        self.date = timezone.now().replace(month=6, day=10)
        jobposition = JobPosition.objects.create(name='name 0')
        user = User.objects.create_user('testuser', email='testuser@test.com', password='testing')
        user.save()
        self.employee = Employee.objects.create(user=user,
                                                start_contract=self.date,
                                                occupation=jobposition)

        patient = Patient.objects.create(first_name='first name',
                                         name='name')

        self.invoice_item = InvoiceItem.objects.create(invoice_number='936 some invoice_number',
                                                       invoice_date=self.date,
                                                       patient=patient)

        self.care_code_first = CareCode.objects.create(code='code0',
                                                       name='some name',
                                                       description='description',
                                                       reimbursed=False)
        self.care_code_second = CareCode.objects.create(code='code1',
                                                        name='some name1',
                                                        description='description1',
                                                        reimbursed=False)
        self.care_code_third = CareCode.objects.create(code='code2',
                                                       name='some name2',
                                                       description='description2',
                                                       reimbursed=False)
        self.care_code_third.save()
        self.care_code_third.exclusive_care_codes.add(self.care_code_first)
        self.care_code_third.exclusive_care_codes.add(self.care_code_second)

        self.existing_prestation = Prestation.objects.create(invoice_item=self.invoice_item,
                                                             employee=self.employee,
                                                             carecode=self.care_code_third,
                                                             date=self.date)

        start_date = timezone.now().replace(month=7, day=10)
        end_date = timezone.now().replace(month=8, day=10)
        self.hospitalization = Hospitalization.objects.create(start_date=start_date,
                                                              end_date=end_date,
                                                              patient=patient)

    def test_is_carecode_valid(self):
        self.assertFalse(Prestation.is_carecode_valid(None, self.care_code_first, self.invoice_item, self.date))
        self.assertFalse(Prestation.is_carecode_valid(None, self.care_code_second, self.invoice_item, self.date))
        self.assertFalse(Prestation.is_carecode_valid(None, self.care_code_third, self.invoice_item, self.date))
        self.assertTrue(
            Prestation.is_carecode_valid(self.existing_prestation.id, self.care_code_second, self.invoice_item,
                                         self.date))

        self.assertTrue(Prestation.is_carecode_valid(None, self.care_code_third, self.invoice_item,
                                                     self.date.replace(month=5, day=1)))

    def test_string_representation(self):
        carecode = CareCode(code='code',
                            name='some name',
                            description='description',
                            reimbursed=False)

        prestation = Prestation(carecode=carecode)

        self.assertEqual(str(prestation), '%s - %s' % (prestation.carecode.code, prestation.carecode.name))

    def test_autocomplete(self):
        self.assertEqual(Prestation.autocomplete_search_fields(), ('patient__name', 'patient__first_name'))

    def test_is_patient_hospitalized(self):
        error_msg = {'date': 'Patient has hospitalization records for the chosen date'}
        data = {
            'date': self.hospitalization.start_date.replace(day=9),
            'invoice_item_id': self.invoice_item.id
        }

        self.assertEqual(Prestation.validate_patient_hospitalization(data), {})

        data['date'] = self.hospitalization.start_date
        self.assertEqual(Prestation.validate_patient_hospitalization(data), error_msg)

        data['date'] = data['date'].replace(month=7, day=20)
        self.assertEqual(Prestation.validate_patient_hospitalization(data), error_msg)

        data['date'] = self.hospitalization.end_date
        self.assertEqual(Prestation.validate_patient_hospitalization(data), error_msg)

        data['date'] = data['date'].replace(day=11)
        self.assertEqual(Prestation.validate_patient_hospitalization(data), {})


class InvoiceItemTestCase(TestCase):
    def setUp(self):
        patient = Patient.objects.create(first_name='first name',
                                         name='name')

        date = datetime.now()
        InvoiceItem.objects.create(invoice_number='936 some invoice_number',
                                   invoice_date=date,
                                   patient=patient)
        InvoiceItem.objects.create(invoice_number='10',
                                   invoice_date=date,
                                   patient=patient)
        InvoiceItem.objects.create(invoice_number='058',
                                   invoice_date=date,
                                   patient=patient)
        InvoiceItem.objects.create(invoice_number='147',
                                   invoice_date=date,
                                   patient=patient)
        InvoiceItem.objects.create(invoice_number='259',
                                   invoice_date=date,
                                   patient=patient)
        InvoiceItem.objects.create(invoice_number='926',
                                   invoice_date=date,
                                   patient=patient)

    def test_string_representation(self):
        patient = Patient(first_name='first name',
                          name='name')

        invoice_item = InvoiceItem(patient=patient,
                                   invoice_number='some invoice_number')

        self.assertEqual(str(invoice_item),
                         'invocie no.: %s - nom patient: %s' % (invoice_item.invoice_number, invoice_item.patient))

    def test_autocomplete(self):
        self.assertEqual(InvoiceItem.autocomplete_search_fields(), ('invoice_number',))

    def test_invoice_month(self):
        date = datetime.now()
        invoice_item = InvoiceItem(invoice_date=date)

        self.assertEqual(invoice_item.invoice_month, date.strftime("%B %Y"))

    def test_default_invoice_number(self):
        self.assertEqual(get_default_invoice_number(), 927)


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

        self.invoice_item = InvoiceItem.objects.create(invoice_number='936 some invoice_number',
                                                       invoice_date=self.start_date,
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
        error_msg = {'start_date': 'Prestation(s) exist in selected dates range for this Patient'}
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
