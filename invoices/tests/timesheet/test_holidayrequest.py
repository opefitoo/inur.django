from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from invoices.employee import Employee, EmployeeContractDetail, JobPosition
from invoices.enums.generic import HolidayRequestChoice
from invoices.enums.holidays import HolidayRequestWorkflowStatus
from invoices.holidays import HolidayRequest, validate_date_range


class HolidayRequestTestCase(TestCase):

    def setUp(self):
        self.start_date = timezone.now().replace(month=6, day=1)
        self.end_date = timezone.now().replace(month=6, day=20)

        self.user = User.objects.create_user('testuser', email='testuser@test.com', password='testing')
        self.user.save()
        jobposition = JobPosition.objects.create(name='name 0')
        jobposition.save()
        self.employee = Employee.objects.create(user=self.user,
                                                start_contract=self.start_date,
                                                occupation=jobposition)
        self.employee.save()
        employee_detail = EmployeeContractDetail.objects.create(
            start_date=timezone.now().replace(year=2018, month=6, day=1),
            number_of_hours=30,
            employee_link=self.employee)
        employee_detail.save()

        self.u1 = User.objects.create_user('u1', email='u1@test.com', password='testing')
        self.u1.save()
        job_position1 = JobPosition.objects.create(name='name u1')
        job_position1.save()
        self.employee_u1 = Employee.objects.create(user=self.u1,
                                                   start_contract=self.start_date,
                                                   occupation=job_position1)
        self.employee_u1.save()
        employee_detail_1 = EmployeeContractDetail.objects.create(
            start_date=timezone.now().replace(year=2018, month=6, day=1),
            number_of_hours=30,
            employee_link=self.employee_u1)
        employee_detail_1.save()

        self.u2 = User.objects.create_user('u2', email='u2@test.com', password='testing')
        self.u2.save()
        job_position2 = JobPosition.objects.create(name='name u2')
        job_position2.save()
        self.employee_u2 = Employee.objects.create(user=self.u2,
                                                   start_contract=self.start_date,
                                                   occupation=job_position2)
        self.employee_u2.save()
        employee_detail_2 = EmployeeContractDetail.objects.create(
            start_date=timezone.now().replace(year=2017, month=1, day=1),
            number_of_hours=40,
            employee_link=self.employee_u2)
        employee_detail_2.save()

    def tearDown(self):
        self.employee.delete()
        self.user.delete()
        self.employee_u1.delete()
        self.u1.delete()
        self.employee_u2.delete()
        self.u2.delete()

    def test_u1_from_18_02_21_to_26_02_21_u2_from_13_02_21_to_20_02_21(self):
        data = {
            'start_date': timezone.now().replace(year=2021, month=2, day=18, hour=8, minute=00),
            'end_date': timezone.now().replace(year=2020, month=2, day=26, hour=16, minute=00),
            'employee_id': self.u1
        }
        # create holiday request but now being validated
        another_holiday_request = HolidayRequest.objects.create(employee=self.u2,
                                                                start_date=timezone.now().replace(year=2021, month=2,
                                                                                                  day=8),
                                                                end_date=timezone.now().replace(year=2021, month=2,
                                                                                                day=20),
                                                                requested_period=HolidayRequestChoice.req_full_day,
                                                                reason=1,
                                                                request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        another_holiday_request.save()
        self.assertEqual(validate_date_range(1234567890, data),
                         {'start_date': "Intersection avec d'autres demandes Congés de u2 - du  2021-02-08 au "
                                        "2021-02-20 "})

    def test_u1_from_18_01_21_to_26_01_21_u2_from_13_02_21_to_20_02_21(self):
        # no intersection
        data = {
            'start_date': timezone.now().replace(year=2021, month=1, day=18, hour=8, minute=00),
            'end_date': timezone.now().replace(year=2020, month=1, day=26, hour=16, minute=00),
            'employee_id': self.u1
        }
        # create holiday request but now being validated
        another_holiday_request = HolidayRequest.objects.create(employee=self.u2,
                                                                start_date=timezone.now().replace(year=2021, month=2,
                                                                                                  day=8),
                                                                end_date=timezone.now().replace(year=2021, month=2,
                                                                                                day=20),
                                                                requested_period=HolidayRequestChoice.req_full_day,
                                                                reason=1,
                                                                request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        another_holiday_request.save()
        self.assertEqual(validate_date_range(1234567890, data), {})