from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from invoices.employee import Employee, EmployeeContractDetail, JobPosition
from invoices.enums.generic import HolidayRequestChoice
from invoices.enums.holidays import HolidayRequestWorkflowStatus
from invoices.holidays import HolidayRequest
from invoices.timesheet import TimesheetTask, TimesheetDetail, \
    validate_date_range_vs_holiday_requests, SimplifiedTimesheet


class JobPositionTestCase(TestCase):
    def test_string_representation(self):
        job_position = JobPosition(name='some name')

        self.assertEqual(str(job_position), '%s' % (job_position.name.strip()))


class EmployeeTestCase(TestCase):
    def test_string_representation(self):
        user = User(username='Some_username')
        employee = Employee(user=user, abbreviation="SU")

        self.assertEqual(str(employee), '%s (%s)' % (employee.user.username.strip(), employee.abbreviation))

    def test_autocomplete(self):
        self.assertEqual(Employee.autocomplete_search_fields(),
                         ('occupation__name', 'user__first_name', 'user__last_name', 'user__username'))


class TimesheetTaskTestCase(TestCase):
    def test_string_representation(self):
        timesheet_task = TimesheetTask(name='some name')

        self.assertEqual(str(timesheet_task), '%s' % (timesheet_task.name.strip()))

    def test_autocomplete(self):
        self.assertEqual(TimesheetTask.autocomplete_search_fields(), 'name')


class TimesheetDetailTestCase(TestCase):

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

    def test_string_representation(self):
        timesheet_detail = TimesheetDetail()

        self.assertEqual(str(timesheet_detail), '')

    def test_validate_date_range_vs_holiday_requests_no_intersect(self):
        data = {
            'start_date': timezone.now().replace(month=6, day=10, hour=8, minute=00),
            'end_date': timezone.now().replace(month=6, day=10, hour=16, minute=00),
        }
        self.assertEqual(validate_date_range_vs_holiday_requests(data, self.employee.id), {})
        # create holiday request but not validated yet
        holiday_request = HolidayRequest.objects.create(employee=self.user,
                                                        start_date=timezone.now().replace(month=6, day=8),
                                                        end_date=timezone.now().replace(month=6, day=12),
                                                        requested_period=HolidayRequestChoice.req_full_day,
                                                        reason=1)
        holiday_request.save()
        self.assertEqual(validate_date_range_vs_holiday_requests(data, self.user.id), {})

    def test_validate_date_range_vs_holiday_requests_intersect(self):
        data = {
            'start_date': timezone.now().replace(year=2020, month=6, day=10, hour=8, minute=00),
            'end_date': timezone.now().replace(year=2020, month=6, day=10, hour=16, minute=00),
        }
        # create holiday request but now being validated
        another_holiday_request = HolidayRequest.objects.create(employee=self.user,
                                                                start_date=timezone.now().replace(year=2020, month=6,
                                                                                                  day=10),
                                                                end_date=timezone.now().replace(year=2020, month=6,
                                                                                                day=12),
                                                                requested_period=HolidayRequestChoice.req_full_day,
                                                                reason=1,
                                                                request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        another_holiday_request.save()
        self.assertEqual(validate_date_range_vs_holiday_requests(data, self.user.id),
                         {'start_date': "Intersection avec des demandes d'absence de : 2020-06-10 à 2020-06-12"})

    def test_validate_date_range_vs_holiday_requests_intersect_with_holidays_outside(self):
        data = {
            'start_date': timezone.now().replace(year=2020, month=6, day=10, hour=8, minute=00),
            'end_date': timezone.now().replace(year=2020, month=6, day=10, hour=16, minute=00),
        }
        # create holiday request but now being validated
        another_holiday_request = HolidayRequest.objects.create(employee=self.user,
                                                                start_date=timezone.now().replace(year=2020, month=6,
                                                                                                  day=8),
                                                                end_date=timezone.now().replace(year=2020, month=6,
                                                                                                day=20),
                                                                requested_period=HolidayRequestChoice.req_full_day,
                                                                reason=1,
                                                                request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        another_holiday_request.save()
        self.assertEqual(validate_date_range_vs_holiday_requests(data, self.user.id),
                         {'start_date': "Intersection avec des demandes d'absence de : 2020-06-08 à 2020-06-20"})

    #
    # def test_u1_from_22_02_21_to_26_02_21_u2_from_13_02_21_to_20_02_21(self):
    #     data = {
    #         'start_date': timezone.now().replace(year=2021, month=2, day=22, hour=8, minute=00),
    #         'end_date': timezone.now().replace(year=2020, month=2, day=26, hour=16, minute=00),
    #     }
    #     # create holiday request but now being validated
    #     another_holiday_request = HolidayRequest.objects.create(employee=self.u1,
    #                                                             start_date=timezone.now().replace(year=2020, month=2,
    #                                                                                               day=8),
    #                                                             end_date=timezone.now().replace(year=2020, month=2,
    #                                                                                             day=20),
    #                                                             half_day=False,
    #                                                             reason=1,
    #                                                             request_status=HolidayRequest.HolidayRequestWorkflowStatus.ACCEPTED)
    #     another_holiday_request.save()
    #     self.assertEqual(validate_date_range_vs_holiday_requests(data, self.u1.id),
    #                      {'start_date': "Intersection avec des demandes d'absence de : 2020-06-08 à 2020-06-20"})

    def test_calculate_holiday_requests_for_specific_period(self):
        # data = {
        #     'start_date': timezone.now().replace(month=6, day=1, hour=8, minute=00),
        #     'end_date': timezone.now().replace(month=6, day=10, hour=16, minute=00),
        # }
        # create holiday request but now being validated
        holiday_request = HolidayRequest.objects.create(employee=self.user,
                                                        start_date=timezone.now().replace(day=19),
                                                        end_date=timezone.now().replace(day=20),
                                                        requested_period=HolidayRequestChoice.req_full_day,
                                                        reason=1,
                                                        request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        holiday_request.save()

        simplified_timesheet = SimplifiedTimesheet.objects.create(employee=self.employee,
                                                                  time_sheet_year=timezone.now().year,
                                                                  time_sheet_month=timezone.now().month,
                                                                  user=self.user)
        simplified_timesheet.save()
        self.assertEqual(6, simplified_timesheet.absence_hours_taken()[0])

    def test_calculate_holiday_requests_for_period_outside_times(self):
        # data = {
        #     'start_date': timezone.now().replace(month=6, day=1, hour=8, minute=00),
        #     'end_date': timezone.now().replace(month=6, day=30, hour=16, minute=00),
        # }
        # create holiday request but now being validated
        holiday_request = HolidayRequest.objects.create(employee=self.user,
                                                        start_date=timezone.now().replace(month=6, day=1),
                                                        end_date=timezone.now().replace(month=6, day=30),
                                                        requested_period=HolidayRequestChoice.req_full_day,
                                                        reason=1,
                                                        request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        holiday_request.save()

        simplified_timesheet = SimplifiedTimesheet.objects.create(employee=self.employee,
                                                                  time_sheet_year=timezone.now().year,
                                                                  time_sheet_month=7,
                                                                  user=self.user)
        simplified_timesheet.save()
        self.assertEqual(0, simplified_timesheet.absence_hours_taken()[0])
