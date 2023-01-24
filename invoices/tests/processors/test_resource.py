from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from invoices.employee import JobPosition, Employee, EmployeeContractDetail
from invoices.timesheet import SimplifiedTimesheet, SimplifiedTimesheetDetail


class DoorEventTestCase(TestCase):

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

    def test_initial(self):
        simplified_timesheet = SimplifiedTimesheet.objects.create(employee=self.employee,
                                                                  time_sheet_year=timezone.now().year,
                                                                  time_sheet_month=timezone.now().month,
                                                                  user=self.user)
        # simplified_timesheet.save()
        SimplifiedTimesheetDetail.objects.create(
            start_date=timezone.now().replace(year=timezone.now().year, month=timezone.now().month, day=1, hour=6,
                                              minute=0, second=0, microsecond=0),
            end_date=timezone.now().replace(year=timezone.now().year, month=timezone.now().month, day=1, hour=14,
                                            minute=15, second=0, microsecond=0),
            simplified_timesheet=simplified_timesheet)
        simplified_timesheet.save()
        #get_door_events_for_employee(employee=self.employee)
