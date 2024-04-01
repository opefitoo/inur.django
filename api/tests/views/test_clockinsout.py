from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.clockinserializers import SimplifiedTimesheetClockInOutSerializer
from invoices.employee import JobPosition, Employee, EmployeeContractDetail


class SimplifiedTimesheetViewTest(APITestCase):
    def setUp(self):
        self.start_date = timezone.now().replace(month=6, day=1)
        self.end_date = timezone.now().replace(month=6, day=20)

        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        jobposition = JobPosition.objects.create(name='name 0')
        jobposition.save()
        self.employee = Employee.objects.create(user=self.user,
                                                start_contract=self.start_date,
                                                occupation=jobposition)
        self.employee.save()
        employee_detail = EmployeeContractDetail.objects.create(
            start_date=timezone.now().replace(year=2018, month=6, day=1),
            number_of_hours=32,
            employee_link=self.employee, number_of_days_holidays=26)
        employee_detail.save()

        self.simplified_timesheet_data = {
            "employee": self.employee.id,
            "time_sheet_year": 2023,
            "time_sheet_month": 3,
            "clock_in": "2023-03-15T09:00:00Z",  # Replace with the actual clock-in time
        }

    def test_simplified_timesheet_clock_in_view(self):
        response = self.client.post(reverse('simplified_timesheet_clock_in'), self.simplified_timesheet_data,
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_simplified_timesheet_clock_out_view(self):
        # First, create a SimplifiedTimesheet instance
        self.client.post(reverse('simplified_timesheet_clock_in'), data=self.simplified_timesheet_data, format='json')

        # Then, clock out
        response = self.client.post(reverse('simplified_timesheet_clock_out'), data=self.simplified_timesheet_data,
                                    format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

class SimplifiedTimesheetClockInOutSerializerTest(TestCase):
    def setUp(self):
        self.start_date = timezone.now().replace(month=6, day=1)
        self.end_date = timezone.now().replace(month=6, day=20)

        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='12345')
        self.client.login(username='testuser', password='12345')
        jobposition = JobPosition.objects.create(name='name 0')
        jobposition.save()
        self.employee = Employee.objects.create(user=self.user,
                                                start_contract=self.start_date,
                                                occupation=jobposition)
        self.employee.save()
        employee_detail = EmployeeContractDetail.objects.create(
            start_date=timezone.now().replace(year=2018, month=6, day=1),
            number_of_hours=32,
            employee_link=self.employee, number_of_days_holidays=26)
        employee_detail.save()

        self.simplified_timesheet_data = {
            "employee": self.employee.id,
            "time_sheet_year": 2023,
            "time_sheet_month": 3,
            "clock_in": "2023-03-15T09:00:00Z",  # Replace with the actual clock-in time
        }
        self.serializer = SimplifiedTimesheetClockInOutSerializer(data=self.simplified_timesheet_data)

    def test_serializer_with_valid_data(self):
        self.assertTrue(self.serializer.is_valid())

    def test_serializer_with_invalid_data(self):
        self.serializer = SimplifiedTimesheetClockInOutSerializer(data={})
        self.assertFalse(self.serializer.is_valid())
