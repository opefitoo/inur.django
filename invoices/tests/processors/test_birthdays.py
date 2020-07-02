from django.test import TestCase
from django.utils import timezone

from invoices.models import Patient
from invoices.processors.birthdays import list_patients_with_birth_date_in_range_still_alive, process_and_generate


class BirthdayTestCase(TestCase):
    def test_list_patients_with_birth_date_in_range(self):
        Patient.objects.create(code_sn='1977030661534',
                               first_name='I WANT THIS PATIENT',
                               name='name 0',
                               address='address 0',
                               zipcode='zipcode 0',
                               city='city 0',
                               phone_number='000')

        Patient.objects.create(code_sn='1977030861534',
                               first_name='I DONT WANT THIS PATIENT',
                               name='name 0',
                               address='address 0',
                               zipcode='zipcode 0',
                               city='city 0',
                               phone_number='000')

        start = timezone.now().replace(month=3, day=6)
        end = timezone.now().replace(month=3, day=7)
        patients = list_patients_with_birth_date_in_range_still_alive(start, end)
        self.assertEqual(len(patients), 1)
        self.assertEqual(patients[0].first_name, 'I WANT THIS PATIENT')

    def test_list_patients_born_in_2000s(self):
        Patient.objects.create(code_sn='2004070908995',
                               first_name='I WANT THIS PATIENT',
                               name='name 0',
                               address='address 0',
                               zipcode='zipcode 0',
                               city='city 0',
                               phone_number='000')

        Patient.objects.create(code_sn='2001030861534',
                               first_name='I DONT WANT THIS PATIENT',
                               name='name 0',
                               address='address 0',
                               zipcode='zipcode 0',
                               city='city 0',
                               phone_number='000')

        start = timezone.now().replace(month=7, day=2)
        end = timezone.now().replace(month=8, day=1)
        patients = list_patients_with_birth_date_in_range_still_alive(start, end)
        self.assertEqual(len(patients), 1)
        self.assertEqual(patients[0].first_name, 'I WANT THIS PATIENT')

    def test_list_patients_with_birth_date_in_range_with_dead_patient(self):
        Patient.objects.create(code_sn='1977030661534',
                               first_name='I WANT THIS PATIENT',
                               name='name 0',
                               address='address 0',
                               zipcode='zipcode 0',
                               city='city 0',
                               phone_number='000',
                               date_of_death=timezone.now())

        start = timezone.now().replace(month=3, day=6)
        end = timezone.now().replace(month=3, day=7)
        patients = list_patients_with_birth_date_in_range_still_alive(start, end)
        self.assertEqual(len(patients), 0)

    def test_list_patients_with_birth_date_in_range_between_december_and_january(self):
        Patient.objects.create(code_sn='1978123161534',
                               first_name='I WANT THIS PATIENT',
                               name='name 0',
                               address='address 0',
                               zipcode='zipcode 0',
                               city='city 0',
                               phone_number='000')

        Patient.objects.create(code_sn='1979010561534',
                               first_name='I WANT THIS PATIENT TOO',
                               name='name 0',
                               address='address 0',
                               zipcode='zipcode 0',
                               city='city 0',
                               phone_number='000')

        Patient.objects.create(code_sn='198001661534',
                               first_name='I DONT WANT THIS PATIENT',
                               name='name 0',
                               address='address 0',
                               zipcode='zipcode 0',
                               city='city 0',
                               phone_number='000')

        Patient.objects.create(code_sn='1960123061534',
                               first_name='I DONT WANT THIS PATIENT TOO',
                               name='name 0',
                               address='address 0',
                               zipcode='zipcode 0',
                               city='city 0',
                               phone_number='000')

        start = timezone.now().replace(year=2019, month=12, day=31)
        end = timezone.now().replace(year=2020, month=1, day=5)
        patients = list_patients_with_birth_date_in_range_still_alive(start, end)
        self.assertEqual(len(patients), 2)

    def test_process_and_generate(self):
        built_code_sn = '1977' + str(timezone.now().month).zfill(2) + str(timezone.now().day).zfill(2) + '61534'
        Patient.objects.create(code_sn=built_code_sn,
                               first_name='I WANT THIS PATIENT',
                               name='name 0',
                               address='address 0',
                               zipcode='zipcode 0',
                               city='city 0',
                               phone_number='000')

        result = process_and_generate(30)
        self.assertEqual(len(result), 1)


