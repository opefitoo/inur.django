from django.test import TestCase
from django.contrib.auth.models import User

from invoices.timesheet import JobPosition, Employee, Timesheet, TimesheetTask, TimesheetDetail


class JobPositionTestCase(TestCase):
    def test_string_representation(self):
        job_position = JobPosition(name='some name')

        self.assertEqual(str(job_position), '%s' % (job_position.name.strip()))


class EmployeeTestCase(TestCase):
    def test_string_representation(self):
        user = User(username='some_username')
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
    def test_string_representation(self):
        timesheet_detail = TimesheetDetail()

        self.assertEqual(str(timesheet_detail), '')
