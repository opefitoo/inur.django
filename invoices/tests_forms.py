from django.utils import timezone
from django.forms import inlineformset_factory, ValidationError
from django.test import TestCase

from invoices.forms import ValidityDateFormSet, check_for_periods_intersection
from invoices.models import CareCode, ValidityDate


class CheckForPeriodsIntersectionTestCase(TestCase):
    def setUp(self):
        date = timezone.now()
        self.start_date = date.replace(month=4, day=1)
        self.end_date = date.replace(month=8, day=1)
        self.periods = [
            {
                'start_date': self.start_date,
                'end_date': self.end_date
            },
            {
                'start_date': self.start_date,
                'end_date': self.end_date
            }
        ]

    def test_equal(self):
        self.assertRaises(ValidationError, check_for_periods_intersection, self.periods)

    def test_contain(self):
        self.periods[1]['start_date'] = self.start_date.replace(month=5, day=1)
        self.periods[1]['end_date'] = self.end_date.replace(month=6, day=1)
        self.assertRaises(ValidationError, check_for_periods_intersection, self.periods)

    def test_intersect_end(self):
        self.periods[1]['start_date'] = self.start_date.replace(month=7, day=1)
        self.periods[1]['end_date'] = self.end_date.replace(month=9, day=1)
        self.assertRaises(ValidationError, check_for_periods_intersection, self.periods)

    def test_intersect_start(self):
        self.periods[1]['start_date'] = self.start_date.replace(month=1, day=1)
        self.periods[1]['end_date'] = self.end_date.replace(month=5, day=1)
        self.assertRaises(ValidationError, check_for_periods_intersection, self.periods)

    def test_end_equal_to_start(self):
        self.periods[1]['start_date'] = self.start_date.replace(month=1, day=1)
        self.periods[1]['end_date'] = self.end_date.replace(month=8, day=1)
        self.assertRaises(ValidationError, check_for_periods_intersection, self.periods)

    def test_start_equal_to_end(self):
        self.periods[1]['start_date'] = self.start_date.replace(month=8, day=1)
        self.periods[1]['end_date'] = self.end_date.replace(month=9, day=1)
        self.assertRaises(ValidationError, check_for_periods_intersection, self.periods)

    def test_before(self):
        self.periods[1]['start_date'] = self.start_date.replace(month=2, day=1)
        self.periods[1]['end_date'] = self.end_date.replace(month=3, day=1)
        self.assertIsNone(check_for_periods_intersection(self.periods))

    def test_after(self):
        self.periods[1]['start_date'] = self.start_date.replace(month=9, day=1)
        self.periods[1]['end_date'] = self.end_date.replace(month=10, day=1)
        self.assertIsNone(check_for_periods_intersection(self.periods))


class ValidityDateFormSetTestCase(TestCase):
    def setUp(self):
        self.care_code = CareCode.objects.create(code='code',
                                                 name='some name',
                                                 description='description',
                                                 reimbursed=False)
        self.formset = inlineformset_factory(CareCode, ValidityDate, formset=ValidityDateFormSet, fields='__all__')
        self.valid_data_single = {
            'validity_dates-INITIAL_FORMS': 0,
            'validity_dates-MAX_NUM_FORMS': 1000,
            'validity_dates-MIN_NUM_FORMS': 0,
            'validity_dates-TOTAL_FORMS': 1,
            'validity_dates-0-care_code': self.care_code.id,
            'validity_dates-0-end_date': '2016-12-31',
            'validity_dates-0-gross_amount': 12.00,
            'validity_dates-0-id': None,
            'validity_dates-0-start_date': '2016-01-01',
        }
        self.valid_data_second = {
            'validity_dates-1-care_code': self.care_code.id,
            'validity_dates-1-end_date': '2017-12-31',
            'validity_dates-1-gross_amount': 52.00,
            'validity_dates-1-id': None,
            'validity_dates-1-start_date': '2017-01-01',
        }
        self.valid_data_third = {
            'validity_dates-2-care_code': self.care_code.id,
            'validity_dates-2-end_date': '',
            'validity_dates-2-gross_amount': 52.00,
            'validity_dates-2-id': None,
            'validity_dates-2-start_date': '2018-01-01',
        }

        self.invalid_data_single = self.valid_data_single.copy()
        self.invalid_data_single['validity_dates-0-end_date'] = '2015-12-31'

        self.valid_data_multiple = self.valid_data_single.copy()
        self.valid_data_multiple['validity_dates-TOTAL_FORMS'] = 3
        self.valid_data_multiple.update(self.valid_data_second)
        self.valid_data_multiple.update(self.valid_data_third)

    def test_date_range_single_valid(self):
        self.formset = self.formset(self.valid_data_single, prefix='validity_dates', instance=self.care_code)
        self.assertTrue(self.formset.is_valid())

    def test_date_range_single_invalid(self):
        self.formset = self.formset(self.invalid_data_single, prefix='validity_dates', instance=self.care_code)
        self.assertFalse(self.formset.is_valid())

    def test_date_range_multiple_valid(self):
        self.formset = self.formset(self.valid_data_multiple, prefix='validity_dates', instance=self.care_code)
        self.assertTrue(self.formset.is_valid())

    def test_date_range_multiple_invalid_intersect_inside(self):
        data = self.valid_data_multiple.copy()
        data['validity_dates-2-start_date'] = '2017-05-31'
        data['validity_dates-2-end_date'] = '2017-06-31'

        self.formset = self.formset(data, prefix='validity_dates', instance=self.care_code)
        self.assertFalse(self.formset.is_valid())

    def test_date_range_multiple_invalid_intersect_start(self):
        data = self.valid_data_multiple.copy()
        data['validity_dates-2-start_date'] = '2015-05-31'
        data['validity_dates-2-end_date'] = '2016-01-01'

        self.formset = self.formset(data, prefix='validity_dates', instance=self.care_code)
        self.assertFalse(self.formset.is_valid())

    def test_date_range_multiple_invalid_contain_start(self):
        data = self.valid_data_multiple.copy()
        data['validity_dates-2-start_date'] = '2015-01-01'
        data['validity_dates-2-end_date'] = '2016-02-01'

        self.formset = self.formset(data, prefix='validity_dates', instance=self.care_code)
        self.assertFalse(self.formset.is_valid())

    def test_date_range_multiple_invalid_intersect_end(self):
        data = self.valid_data_multiple.copy()
        data['validity_dates-2-start_date'] = '2017-12-31'
        data['validity_dates-2-end_date'] = '2018-12-31'

        self.formset = self.formset(data, prefix='validity_dates', instance=self.care_code)
        self.assertFalse(self.formset.is_valid())

    def test_date_range_multiple_invalid_contain_end(self):
        data = self.valid_data_multiple.copy()
        data['validity_dates-2-start_date'] = '2017-11-15'
        data['validity_dates-2-end_date'] = '2018-01-31'

        self.formset = self.formset(data, prefix='validity_dates', instance=self.care_code)
        self.assertFalse(self.formset.is_valid())

    def test_date_range_multiple_invalid_after_none_end(self):
        data = self.valid_data_multiple.copy()
        data_fourth = {
            'validity_dates-3-care_code': self.care_code.id,
            'validity_dates-3-end_date': '2018-12-31',
            'validity_dates-3-gross_amount': 55.00,
            'validity_dates-3-id': None,
            'validity_dates-3-start_date': '2018-01-31',
        }
        data.update(data_fourth)
        data['validity_dates-TOTAL_FORMS'] = 4

        self.formset = self.formset(data, prefix='validity_dates', instance=self.care_code)
        self.assertFalse(self.formset.is_valid())
