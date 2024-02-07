from datetime import timedelta

from dateutil.relativedelta import relativedelta
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from invoices.employee import JobPosition, Employee, EmployeeContractDetail


class EmployeeModelTest(TestCase):
    def setUp(self):
        user = User.objects.create_user('testuser', email='testuser@test.com', password='testing')
        user.save()
        jobposition = JobPosition.objects.create(name='name 0')
        self.employee = Employee.objects.create(user=user,
                                                start_contract=timezone.now().date(),
                                                occupation=jobposition,
                                                )
        # Contract starting 2 months ago and ending last day of last month
        start_date1 = timezone.now().date() - relativedelta(months=2)
        end_date1 = (timezone.now().date().replace(day=1) - timedelta(days=1))
        self.contract1 = EmployeeContractDetail.objects.create(
            start_date=start_date1,
            end_date=end_date1,
            number_of_hours=20,
            employee_link=self.employee,
            number_of_days_holidays=34
        )

        # Contract starting 1st day of current month and still ongoing
        start_date2 = timezone.now().date().replace(day=1)
        self.contract2 = EmployeeContractDetail.objects.create(
            start_date=start_date2,
            end_date=None,  # Ongoing contract
            number_of_hours=30,
            employee_link=self.employee,
            number_of_days_holidays=34
        )

    def test_get_contracts_between_dates(self):
        contracts = self.employee.get_contracts_between_dates(timezone.now().date() - relativedelta(months=1),
                                                              timezone.now().date())
        self.assertEqual(len(contracts), 2)
        self.assertEqual(contracts[0], self.contract1)
        self.assertEqual(contracts[1], self.contract2)

    def test_get_contracts_between_dates_2(self):
        # Start date is the first day of the current month
        start_date = timezone.now().date().replace(day=1)
        # End date is the current date
        end_date = timezone.now().date()

        contracts = self.employee.get_contracts_between_dates(start_date, end_date)

        # The ongoing contract (self.contract2) should be in the result set
        self.assertIn(self.contract2, contracts)
        # The contract that ended last month (self.contract1) should not be in the result set
        self.assertNotIn(self.contract1, contracts)

    def test_get_average_hours_per_week(self):
        # Start date is the first day of the current month
        start_date = timezone.now().date().replace(day=1)
        # End date is the current date
        end_date = timezone.now().date()

        average_hours_per_week = self.employee.get_average_hours_per_week(start_date, end_date)

        # The ongoing contract (self.contract2) is the only contract within the date range
        # So, the average hours per week should be the number of hours for this contract
        self.assertEqual(average_hours_per_week, self.contract2.number_of_hours)

    def test_get_average_hours_per_week_two_contracts(self):
        # Start date is the start date of the first contract
        start_date = self.contract1.start_date
        # End date is the current date
        end_date = timezone.now().date()

        average_hours_per_week = self.employee.get_average_hours_per_week(start_date, end_date)

        # Calculate the expected average hours per week
        weeks_contract1 = (self.contract1.end_date - self.contract1.start_date).days / 7
        weeks_contract2 = (end_date - self.contract2.start_date).days / 7

        # If there's a gap between the end of the first contract and the start of the second contract,
        # consider the number of hours for that period as 0
        gap_weeks = 0
        if self.contract2.start_date > self.contract1.end_date:
            gap_weeks = (self.contract2.start_date - self.contract1.end_date).days / 7

        total_weeks = weeks_contract1 + weeks_contract2 + gap_weeks
        total_hours = self.contract1.number_of_hours * weeks_contract1 + self.contract2.number_of_hours * weeks_contract2
        expected_average_hours_per_week = total_hours / total_weeks if total_weeks > 0 else 0

        self.assertEqual(average_hours_per_week, round(expected_average_hours_per_week, 2))
