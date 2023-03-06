from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from invoices.employee import Employee, EmployeeContractDetail, JobPosition
from invoices.enums.generic import HolidayRequestChoice
from invoices.enums.holidays import HolidayRequestWorkflowStatus
from invoices.holidays import HolidayRequest
from invoices.timesheet import SimplifiedTimesheet, SimplifiedTimesheetDetail


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

    def test_total_holidays_taken_if_no_holiday_taken(self):
        simplified_timesheet = SimplifiedTimesheet.objects.create(employee=self.employee,
                                                                  time_sheet_year=2022,
                                                                  time_sheet_month=7,
                                                                  user=self.user)
        simplified_timesheet.save()
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=1, hour=7, minute=15,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=1, hour=17, minute=25,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=4, hour=7, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=4, hour=17, minute=40,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=5, hour=5, minute=20,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=5, hour=17, minute=10,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=6, hour=7, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=6, hour=17, minute=40,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=7, hour=7, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=7, hour=17, minute=50,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=8, hour=7, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=8, hour=17, minute=0,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=11, hour=7, minute=10,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=11, hour=16, minute=15,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=12, hour=5, minute=30,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=12, hour=17, minute=0,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=13, hour=6, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=13, hour=16, minute=0,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=14, hour=6, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=14, hour=16, minute=0,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=15, hour=7, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=15, hour=17, minute=15,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=18, hour=6, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=18, hour=16, minute=0,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=19, hour=5, minute=30,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=19, hour=16, minute=30,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=20, hour=7, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=20, hour=17, minute=0,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=22, hour=7, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=22, hour=17, minute=0,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=25, hour=7, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=25, hour=17, minute=0,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=26, hour=6, minute=30,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=26, hour=17, minute=25,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=27, hour=7, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=27, hour=17, minute=0,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=28, hour=7, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=28, hour=18, minute=40,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=7, day=29, hour=8, minute=0,
                                              second=0, microsecond=0),
            end_date=timezone.now().replace(year=2022, month=7, day=29, hour=18, minute=10,
                                            second=0, microsecond=0), simplified_timesheet=simplified_timesheet)
        holiday_request = HolidayRequest.objects.create(employee=self.user,
                                                        start_date=timezone.now().replace(year=2022, month=7, day=21),
                                                        end_date=timezone.now().replace(year=2022, month=7, day=21),
                                                        requested_period=HolidayRequestChoice.req_full_day,
                                                        reason=1,
                                                        request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        holiday_request.save()
        self.assertEqual(' + 8.75 heures(s)', simplified_timesheet.hours_should_work)
        self.assertEqual('168 h:45 mn', simplified_timesheet.total_hours)

