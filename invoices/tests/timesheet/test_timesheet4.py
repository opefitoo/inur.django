from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from helpers.timesheet import absence_hours_taken
from invoices.employee import Employee, EmployeeContractDetail, JobPosition
from invoices.enums.generic import HolidayRequestChoice
from invoices.enums.holidays import HolidayRequestWorkflowStatus
from invoices.holidays import HolidayRequest
from invoices.timesheet import SimplifiedTimesheetDetail, SimplifiedTimesheet


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
            number_of_hours=40,
            employee_link=self.employee, number_of_days_holidays=26)
        employee_detail.save()

    def tearDown(self):
        self.employee.delete()
        self.user.delete()

    def test_total_use_case_ch_cece_august_2022(self):
        simplified_timesheet = SimplifiedTimesheet.objects.create(employee=self.employee,
                                                                  time_sheet_year=2022,
                                                                  time_sheet_month=8,
                                                                  user=self.user)
        simplified_timesheet.save()

        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=8, day=1, hour=6, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=8, day=1, hour=14, minute=15,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=8, day=2, hour=4, minute=30,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=8, day=2, hour=14, minute=30,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=8, day=3, hour=6, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=8, day=3, hour=14, minute=0,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=8, day=4, hour=6, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=8, day=4, hour=14, minute=0,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=8, day=6, hour=4, minute=30,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=8, day=6, hour=13, minute=0,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=8, day=7, hour=4, minute=30,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=8, day=7, hour=12, minute=30,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=8, day=8, hour=6, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=8, day=8, hour=14, minute=30,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=8, day=9, hour=11, minute=30,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=8, day=9, hour=22, minute=0,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=8, day=10, hour=13, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=8, day=10, hour=20, minute=30,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=8, day=29, hour=5, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=8, day=29, hour=14, minute=30,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=8, day=30, hour=4, minute=30,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=8, day=30, hour=14, minute=30,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=8, day=31, hour=4, minute=30,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=8, day=31, hour=14, minute=30,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        holiday_request = HolidayRequest.objects.create(employee=self.user,
                                                        start_date=timezone.now().replace(year=2022, month=8, day=11),
                                                        end_date=timezone.now().replace(year=2022, month=8, day=14),
                                                        requested_period=HolidayRequestChoice.req_full_day,
                                                        reason=1,
                                                        request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        holiday_request.save()
        holiday_request2 = HolidayRequest.objects.create(employee=self.user,
                                                         start_date=timezone.now().replace(year=2022, month=8, day=15),
                                                         end_date=timezone.now().replace(year=2022, month=8, day=28),
                                                         requested_period=HolidayRequestChoice.req_full_day,
                                                         reason=1,
                                                         request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        holiday_request2.save()
        self.assertEqual(96, absence_hours_taken(simplified_timesheet).compute_total_hours())
