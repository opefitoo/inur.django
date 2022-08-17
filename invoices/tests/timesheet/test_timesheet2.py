from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from invoices.employee import Employee, EmployeeContractDetail, JobPosition
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

    def test_total_hours_calculations_simplest_case(self):
        # holiday_request = HolidayRequest.objects.create(employee=self.user,
        #                                                 start_date=timezone.now().replace(day=19),
        #                                                 end_date=timezone.now().replace(day=20),
        #                                                 requested_period=HolidayRequestChoice.req_full_day,
        #                                                 reason=1,
        #                                                 request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        # holiday_request.save()

        simplified_timesheet = SimplifiedTimesheet.objects.create(employee=self.employee,
                                                                  time_sheet_year=2022,
                                                                  time_sheet_month=8,
                                                                  user=self.user)
        simplified_timesheet.save()
        SimplifiedTimesheetDetail.objects.create(start_date=timezone.now().replace(year=2022, month=8, day=1, hour=8,
                                                                                   minute=0,
                                                                                   second=0,
                                                                                   microsecond=0),
                                                 end_date=timezone.now().replace(year=2022, month=8, day=1, hour=18,
                                                                                 minute=0,
                                                                                 second=0,
                                                                                 microsecond=0),
                                                 simplified_timesheet=simplified_timesheet)

        self.assertEqual('10 h:0 mn', simplified_timesheet.total_hours)
        SimplifiedTimesheetDetail.objects.create(start_date=timezone.now().replace(year=2022, month=8, day=2, hour=8,
                                                                                   minute=0,
                                                                                   second=0,
                                                                                   microsecond=0),
                                                 end_date=timezone.now().replace(year=2022, month=8, day=2, hour=16,
                                                                                 minute=0,
                                                                                 second=0,
                                                                                 microsecond=0),
                                                 simplified_timesheet=simplified_timesheet)
        self.assertEqual('18 h:0 mn', simplified_timesheet.total_hours)
        self.assertEqual('0 h:0 mn ([])', simplified_timesheet.total_hours_sundays)

    def test_calculations_two_sundays_and_public_holiday_worked(self):
        # holiday_request = HolidayRequest.objects.create(employee=self.user,
        #                                                 start_date=timezone.now().replace(day=19),
        #                                                 end_date=timezone.now().replace(day=20),
        #                                                 requested_period=HolidayRequestChoice.req_full_day,
        #                                                 reason=1,
        #                                                 request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        # holiday_request.save()

        simplified_timesheet = SimplifiedTimesheet.objects.create(employee=self.employee,
                                                                  time_sheet_year=2022,
                                                                  time_sheet_month=8,
                                                                  user=self.user)
        simplified_timesheet.save()
        SimplifiedTimesheetDetail.objects.create(start_date=timezone.now().replace(year=2022, month=8, day=7, hour=8,
                                                                                   minute=0,
                                                                                   second=0,
                                                                                   microsecond=0),
                                                 end_date=timezone.now().replace(year=2022, month=8, day=7, hour=18,
                                                                                 minute=0,
                                                                                 second=0,
                                                                                 microsecond=0),
                                                 simplified_timesheet=simplified_timesheet)

        SimplifiedTimesheetDetail.objects.create(start_date=timezone.now().replace(year=2022, month=8, day=14, hour=8,
                                                                                   minute=0,
                                                                                   second=0,
                                                                                   microsecond=0),
                                                 end_date=timezone.now().replace(year=2022, month=8, day=14, hour=16,
                                                                                 minute=0,
                                                                                 second=0,
                                                                                 microsecond=0),
                                                 simplified_timesheet=simplified_timesheet)
        self.assertEqual('18 h:0 mn', simplified_timesheet.total_hours)
        self.assertEqual("18 h:0 mn (['07/08/2022', '14/08/2022'])", simplified_timesheet.total_hours_sundays)

        SimplifiedTimesheetDetail.objects.create(start_date=timezone.now().replace(year=2022, month=8, day=15, hour=8,
                                                                                   minute=0,
                                                                                   second=0,
                                                                                   microsecond=0),
                                                 end_date=timezone.now().replace(year=2022, month=8, day=15, hour=16,
                                                                                 minute=0,
                                                                                 second=0,
                                                                                 microsecond=0),
                                                 simplified_timesheet=simplified_timesheet)
        self.assertEqual("8 h:0 mn (['15/08/2022'])",
                         simplified_timesheet.total_hours_public_holidays)
