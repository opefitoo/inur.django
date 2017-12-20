from datetime import datetime
from django.test import TestCase

from invoices.models import CareCode, ValidityDate


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
        error_message = {'end_date': 'End date must be bigger than Start date'}
        now = datetime.now()
        data = {
            'start_date': now.replace(month=1),
            'end_date': now.replace(month=12)
        }

        self.assertEqual(ValidityDate.validate_dates(data), {})

        data = {
            'start_date': now.replace(month=12),
            'end_date': now.replace(month=1)
        }
        self.assertEqual(ValidityDate.validate_dates(data), error_message)

        data['start_date'] = now.replace(month=12)
        data['end_date'] = now.replace(month=12)
        self.assertEqual(ValidityDate.validate_dates(data), {})

        data['end_date'] = None
        self.assertEqual(ValidityDate.validate_dates(data), {})
