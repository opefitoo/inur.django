from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from helpers.timesheet import how_many_working_days_in_range, absence_hours_taken
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
            number_of_hours=30,
            employee_link=self.employee, number_of_days_holidays=26)
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
            employee_link=self.employee_u1, number_of_days_holidays=26)
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
            employee_link=self.employee_u2, number_of_days_holidays=26)
        employee_detail_2.save()

    def tearDown(self):
        self.employee.delete()
        self.user.delete()

    def test_total_holidays_taken_if_no_holiday_taken(self):
        simplified_timesheet = SimplifiedTimesheet.objects.create(employee=self.employee,
                                                                  time_sheet_year=2022,
                                                                  time_sheet_month=8,
                                                                  user=self.user)
        simplified_timesheet.save()
        absence_object = absence_hours_taken(simplified_timesheet)
        self.assertEqual(absence_object.holidays_count, 0)
        self.assertEqual(absence_object.daily_working_hours, 0)

    def test_total_holidays_taken_simple_cases(self):
        holiday_request = HolidayRequest.objects.create(employee=self.user,
                                                        start_date=timezone.now().replace(year=2022, month=8, day=19),
                                                        end_date=timezone.now().replace(year=2022, month=8, day=20),
                                                        requested_period=HolidayRequestChoice.req_full_day,
                                                        reason=1,
                                                        request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        holiday_request.save()
        simplified_timesheet = SimplifiedTimesheet.objects.create(employee=self.employee,
                                                                  time_sheet_year=2022,
                                                                  time_sheet_month=8,
                                                                  user=self.user)
        simplified_timesheet.save()

        absence_object = absence_hours_taken(simplified_timesheet)
        self.assertEqual(absence_object.holidays_count, 1)
        self.assertEqual(absence_object.daily_working_hours, 6)
        holiday_request2 = HolidayRequest.objects.create(employee=self.user,
                                                         start_date=timezone.now().replace(year=2022, month=8, day=25),
                                                         end_date=timezone.now().replace(year=2022, month=8, day=31),
                                                         requested_period=HolidayRequestChoice.req_full_day,
                                                         reason=1,
                                                         request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        holiday_request2.save()
        absence_object2 = absence_hours_taken(simplified_timesheet)
        self.assertEqual(absence_object2.holidays_count, 5)
        self.assertEqual(absence_object2.daily_working_hours, 6)
        self.assertEqual(absence_object2.compute_total_hours(), 36)

    def test_total_hours_calculations_simplest_case(self):
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

        self.assertEqual('8 h:0 mn', simplified_timesheet.total_hours)
        SimplifiedTimesheetDetail.objects.create(start_date=timezone.now().replace(year=2022, month=8, day=2, hour=8,
                                                                                   minute=0,
                                                                                   second=0,
                                                                                   microsecond=0),
                                                 end_date=timezone.now().replace(year=2022, month=8, day=2, hour=16,
                                                                                 minute=0,
                                                                                 second=0,
                                                                                 microsecond=0),
                                                 simplified_timesheet=simplified_timesheet)
        self.assertEqual('14 h:0 mn', simplified_timesheet.total_hours)
        self.assertEqual('0 h:0 mn', simplified_timesheet.total_hours_sundays)

    def test_calculations_two_sundays_and_public_holiday_worked(self):
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
        self.assertEqual('14 h:0 mn', simplified_timesheet.total_hours)
        self.assertEqual("14 h:0 mn (['07/08/2022', '14/08/2022'])", simplified_timesheet.total_hours_sundays)

        SimplifiedTimesheetDetail.objects.create(start_date=timezone.now().replace(year=2022, month=8, day=15, hour=8,
                                                                                   minute=0,
                                                                                   second=0,
                                                                                   microsecond=0),
                                                 end_date=timezone.now().replace(year=2022, month=8, day=15, hour=16,
                                                                                 minute=0,
                                                                                 second=0,
                                                                                 microsecond=0),
                                                 simplified_timesheet=simplified_timesheet)
        self.assertEqual("6 h:0 mn (['15/08/2022'])",
                         simplified_timesheet.total_hours_public_holidays)

    def test_how_many_working_days_in_range(self):
        start_date = timezone.now().replace(year=2022, month=8, day=1)
        self.assertEqual(how_many_working_days_in_range(start_date.date()), 22)

        start_date = timezone.now().replace(year=2022, month=5, day=1)
        end_date = timezone.now().replace(year=2022, month=5, day=31)
        self.assertEqual(how_many_working_days_in_range(start_date.date()), 20)

    def test_calculations_balance(self):
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
        self.assertEqual('14 h:0 mn', simplified_timesheet.total_hours)
        self.assertEqual(132, simplified_timesheet.total_legal_working_hours)
        self.assertEqual('-118.00 heures(s)', simplified_timesheet.hours_should_work)

    def test_calculations_balance_if_holidays_taken(self):
        holiday_request = HolidayRequest.objects.create(employee=self.user,
                                                        start_date=timezone.now().replace(year=2022, month=8, day=2),
                                                        end_date=timezone.now().replace(year=2022, month=8, day=31),
                                                        requested_period=HolidayRequestChoice.req_full_day,
                                                        reason=1,
                                                        request_status=HolidayRequestWorkflowStatus.ACCEPTED)
        holiday_request.save()

        simplified_timesheet = SimplifiedTimesheet.objects.create(employee=self.employee,
                                                                  time_sheet_year=2022,
                                                                  time_sheet_month=8,
                                                                  user=self.user)
        simplified_timesheet.save()
        d = SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=2022, month=8, day=1, hour=8,
                                              minute=0,
                                              second=0,
                                              microsecond=0),
            end_date=timezone.now().replace(year=2022, month=8, day=1, hour=18,
                                            minute=0,
                                            second=0,
                                            microsecond=0),
            simplified_timesheet=simplified_timesheet)
        d.save()
        self.assertEqual('8 h:0 mn', simplified_timesheet.total_hours)
        self.assertEqual(132, simplified_timesheet.total_legal_working_hours)
        self.assertEqual(126, simplified_timesheet.total_hours_holidays_and_sickness_taken)
        self.assertEqual(' + 2.00 heures(s)', simplified_timesheet.hours_should_work)
