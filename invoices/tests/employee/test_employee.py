from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from invoices.models.employee import Employee, EmployeeContractDetail, JobPosition
from invoices.models.holidays import HolidayRequest


class EmployeeTestCase(TestCase):
    def setUp(self):
        self.start_date = timezone.now().replace(month=6, day=1)
        self.end_date = timezone.now().replace(month=6, day=20)

        self.user = User.objects.create_user('testuser', email='testuser@test.com', password='testing')
        self.user.save()
        jobposition = JobPosition.objects.create(name='name 0')
        jobposition.save()
        self.employee = Employee.objects.create(user=self.user,
                                                user_id=self.user.id,
                                                start_contract=self.start_date,
                                                occupation=jobposition)
        self.employee.save()
        employee_detail = EmployeeContractDetail.objects.create(
            start_date=timezone.now().replace(year=2018, month=6, day=1),
            number_of_hours=30,
            employee_link=self.employee)
        employee_detail.save()

    def test_holidays_taken(self):
        employee = Employee(user=self.user)

        holiday_request = HolidayRequest.objects.create(employee=self.user,
                                                        start_date=timezone.now().replace(month=6, day=1),
                                                        end_date=timezone.now().replace(month=6, day=30),
                                                        half_day=False,
                                                        reason=1,
                                                        request_accepted=True)
        holiday_request.save()

        self.assertEqual(0, employee.holidays_taken())

