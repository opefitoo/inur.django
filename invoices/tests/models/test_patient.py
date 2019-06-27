from django.test import TestCase

from invoices.models import Patient


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
        instance_id = None
        error_messages = {
            'format': {'code_sn': 'Code SN should start with non zero digit and be followed by 12 digits'},
            'unique': {'code_sn': 'Code SN must be unique'}
        }
        data = {
            'code_sn': '0123',
        }
        self.assertEqual(Patient.validate_code_sn(instance_id, data), {})

        data['is_private'] = True
        self.assertEqual(Patient.validate_code_sn(instance_id, data), {})

        data['is_private'] = False
        self.assertEqual(Patient.validate_code_sn(instance_id, data), error_messages['format'])

        data['code_sn'] = '0245789764822'
        self.assertEqual(Patient.validate_code_sn(instance_id, data), error_messages['format'])

        data['code_sn'] = '1245789764822'
        self.assertEqual(Patient.validate_code_sn(instance_id, data), error_messages['unique'])

        data['code_sn'] = '2245789764822'
        self.assertEqual(Patient.validate_code_sn(instance_id, data), {})

    def test_format_code_sn(self):
        code_sn = ' 0 2 4 5 7 8 9 7 6 4 8 2 2 '
        self.assertEqual(Patient.format_code_sn(code_sn, True), code_sn.replace(" ", ""))
        self.assertEqual(Patient.format_code_sn(code_sn, False), code_sn)

        code_sn = '1245 78 97 648 22'
        self.assertEqual(Patient.format_code_sn(code_sn, True), code_sn.replace(" ", ""))
        self.assertEqual(Patient.format_code_sn(code_sn, False), code_sn)

        code_sn = 'weq 22 45s 78976 4 822 as'
        self.assertEqual(Patient.format_code_sn(code_sn, True), code_sn.replace(" ", ""))
        self.assertEqual(Patient.format_code_sn(code_sn, False), code_sn)
