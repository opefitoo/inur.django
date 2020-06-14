from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone

from invoices.holidays import HolidayRequest
from invoices.timesheet import JobPosition, Employee, Timesheet, TimesheetTask, TimesheetDetail, \
    validate_date_range_vs_holiday_requests


class JobPositionTestCase(TestCase):
    def test_string_representation(self):
        job_position = JobPosition(name='some name')

        self.assertEqual(str(job_position), '%s' % (job_position.name.strip()))


class EmployeeTestCase(TestCase):
    def test_string_representation(self):
        user = User(username='Some_username')
        employee = Employee(user=user)

        self.assertEqual(str(employee), '%s' % (employee.user.username.strip()))

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
        self.start_date = timezone.now().replace(month=1, day=10)
        self.end_date = timezone.now().replace(month=6, day=10)

        self.user = User.objects.create_user('testuser', email='testuser@test.com', password='testing')
        self.user.save()
        jobposition = JobPosition.objects.create(name='name 0')
        self.employee = Employee.objects.create(user=self.user,
                                                start_contract=self.start_date,
                                                occupation=jobposition)

    def test_string_representation(self):
        timesheet_detail = TimesheetDetail()

        self.assertEqual(str(timesheet_detail), '')

    def test_validate_date_range_vs_holiday_requests(self):
        data = {
            'start_date': timezone.now().replace(month=6, day=10),
            'end_date': timezone.now().replace(month=6, day=11)
        }
        self.assertEqual(validate_date_range_vs_holiday_requests(data, self.employee.id), {})
        # create holiday request but not validated yet
        holiday_request = HolidayRequest.objects.create(employee=self.user,
                                                        start_date=self.start_date,
                                                        end_date=self.end_date,
                                                        half_day=False,
                                                        reason=1,
                                                        request_accepted=False)
        holiday_request.save()
        self.assertEqual(validate_date_range_vs_holiday_requests(data, self.employee.id), {})

        # create holiday request but now being validated
        another_holiday_request = HolidayRequest.objects.create(employee=self.user,
                                                                start_date=timezone.now().replace(month=6, day=10),
                                                                end_date=timezone.now().replace(month=6, day=12),
                                                                half_day=False,
                                                                reason=1,
                                                                request_accepted=True)
        another_holiday_request.save()
        self.assertEqual(validate_date_range_vs_holiday_requests(data, self.employee.id),
                         {'start_date': "Intersection avec des demandes d'absence de : 2020-06-10 à 2020-06-12"})
