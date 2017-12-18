from django.test import TestCase
from invoices.models import CareCode


class CareCodeTestCase(TestCase):
    def test_string_representation(self):
        carecode = CareCode(code='code',
                            name='some name',
                            description='description',
                            reimbursed=False)

        self.assertEqual(str(carecode), '%s: %s' % (carecode.code, carecode.name))

    def test_autocomplete(self):
        self.assertEqual(CareCode.autocomplete_search_fields(), ('name', 'code'))
