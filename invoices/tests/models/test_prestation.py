from django.utils import timezone
from django.test import TestCase
from django.contrib.auth.models import User

from constance import config
from invoices.models import CareCode, Patient, Prestation, InvoiceItem, Hospitalization
from invoices.employee import Employee, JobPosition
from invoices.modelspackage import InvoicingDetails


class PrestationTestCase(TestCase):
    def setUp(self):
        self.date = timezone.now().replace(month=6, day=10)
        jobposition = JobPosition.objects.create(name='name 0')
        user = User.objects.create_user('testuser', email='testuser@test.com', password='testing')
        user.save()
        invoice_details = InvoicingDetails.objects.create(
            provider_code="111111",
            name="BEST.lu",
            address="Sesame Street",
            zipcode_city="1234 Sesame Street",
            bank_account="LU12 3456 7890 1234 5678")

        self.employee = Employee.objects.create(user=user,
                                                start_contract=self.date,
                                                occupation=jobposition)

        self.patient = Patient.objects.create(first_name='first name',
                                              name='name')

        self.invoice_item = InvoiceItem.objects.create(invoice_number='936 some invoice_number',
                                                       invoice_date=self.date,
                                                      invoice_details=invoice_details,
                                                       patient=self.patient)

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
                                                              patient=self.patient)

    def test_validate_carecode(self):
        data = {
            'carecode': self.care_code_first,
            'invoice_item': self.invoice_item,
            'date': self.date
        }
        self.assertNotEqual(Prestation.validate_carecode(None, data), {})

        data['carecode'] = self.care_code_second
        self.assertNotEqual(Prestation.validate_carecode(None, data), {})

        data['carecode'] = self.care_code_third
        self.assertNotEqual(Prestation.validate_carecode(None, data), {})

        data['carecode'] = self.care_code_second
        self.assertEqual(Prestation.validate_carecode(self.existing_prestation.id, data), {})

        data['carecode'] = self.care_code_third
        data['date'] = data['date'].replace(month=5, day=1)
        self.assertEqual(Prestation.validate_carecode(None, data), {})

    def test_string_representation(self):
        carecode = CareCode(code='code',
                            name='some name',
                            description='description',
                            reimbursed=False)

        prestation = Prestation(carecode=carecode)

        self.assertEqual(str(prestation), '%s - %s' % (prestation.carecode.code, prestation.carecode.name))

    def test_autocomplete(self):
        self.assertEqual(Prestation.autocomplete_search_fields(), ('patient__name', 'patient__first_name'))

    def test_validate_at_home_default_config(self):
        msg = "CareCode %s does not exist. Please create a CareCode with the Code %s" % (
            config.AT_HOME_CARE_CODE, config.AT_HOME_CARE_CODE)
        error_msg = {'at_home': msg}
        data = {
            'at_home': False
        }
        self.assertEqual(Prestation.validate_at_home_default_config(data), {})

        data['at_home'] = True
        CareCode.objects.filter(code=config.AT_HOME_CARE_CODE).delete()
        self.assertEqual(Prestation.validate_at_home_default_config(data), error_msg)

        self.care_code_first = CareCode.objects.create(code=config.AT_HOME_CARE_CODE,
                                                       name='some name',
                                                       description='description',
                                                       reimbursed=False)
        self.assertEqual(Prestation.validate_at_home_default_config(data), {})

    def test_validate_patient_hospitalization(self):
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

    def test_validate_patient_alive(self):
        error_msg = {'date': "Prestation date cannot be later than or equal to Patient's death date"}
        date_of_death = timezone.now().replace(month=6, day=10)
        data = {
            'invoice_item': self.invoice_item,
            'date': date_of_death
        }

        self.assertEqual(Prestation.validate_patient_alive(data), {})

        self.patient.date_of_death = date_of_death.date()
        self.patient.save()

        self.assertEqual(Prestation.validate_patient_alive(data), error_msg)

        data['date'] = data['date'].replace(month=4)
        self.assertEqual(Prestation.validate_patient_alive(data), {})

        data['date'] = data['date'].replace(month=7)
        self.assertEqual(Prestation.validate_patient_alive(data), error_msg)

    def test_paired_at_home_name(self):
        # at_home_care_code = CareCode.objects.create(code=config.AT_HOME_CARE_CODE,
        #                                             name='some name',
        #                                             description='description',
        #                                             reimbursed=False)
        at_home_prestation = Prestation.objects.create(invoice_item=self.invoice_item,
                                                       employee=self.employee,
                                                       carecode=self.care_code_third,
                                                       date=self.date,
                                                       at_home=True)

        self.assertEqual(at_home_prestation.paired_at_home_name, str(at_home_prestation.paired_at_home))

    def test_at_home_paired_name(self):
        # at_home_care_code = CareCode.objects.create(code=config.AT_HOME_CARE_CODE,
        #                                             name='some name',
        #                                             description='description',
        #                                             reimbursed=False)

        at_home_prestation = Prestation.objects.create(invoice_item=self.invoice_item,
                                                       employee=self.employee,
                                                       carecode=self.care_code_third,
                                                       date=self.date,
                                                       at_home=True)
        paired_at_home = at_home_prestation.paired_at_home

        self.assertEqual(paired_at_home.at_home_paired_name, str(paired_at_home.at_home_paired))

    def test_validate_max_limit(self):
        max = InvoiceItem.PRESTATION_LIMIT_MAX
        error_message = {'date': "Max number of Prestations for one InvoiceItem is %s" % (str(max))}

        for index in range(1, max-2):
            Prestation.objects.create(invoice_item=self.invoice_item,
                                      employee=self.employee,
                                      carecode=self.care_code_third,
                                      date=self.date)
        lst_but_one_prestation = Prestation.objects.create(invoice_item=self.invoice_item,
                                                           employee=self.employee,
                                                           carecode=self.care_code_third,
                                                           date=self.date)
        # at_home_care_code = CareCode.objects.create(code=config.AT_HOME_CARE_CODE,
        #                                             name='some name',
        #                                             description='description',
        #                                             reimbursed=False)

        prestation = Prestation(invoice_item=self.invoice_item,
                                employee=self.employee,
                                carecode=self.care_code_third,
                                date=self.date,
                                at_home=False)

        data = prestation.as_dict()
        self.assertEqual(Prestation.validate_max_limit(data), {})

        at_home_prestation = Prestation(invoice_item=self.invoice_item,
                                        employee=self.employee,
                                        carecode=self.care_code_third,
                                        date=self.date,
                                        at_home=True)
        at_home_data = at_home_prestation.as_dict()
        self.assertEqual(Prestation.validate_max_limit(at_home_data), error_message)

        lst_but_one_prestation.at_home = True
        lst_but_one_prestation.save()
        self.assertEqual(Prestation.validate_max_limit(at_home_data), error_message)

        Prestation.objects.create(invoice_item=self.invoice_item,
                                  employee=self.employee,
                                  carecode=self.care_code_third,
                                  date=self.date)

        self.assertEqual(Prestation.validate_max_limit(data), error_message)
        self.assertEqual(Prestation.validate_max_limit(at_home_data), error_message)
