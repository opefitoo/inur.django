from datetime import datetime

from api.tests.views.base import BaseTestCase
from rest_framework.test import APITestCase

from api.serializers import TimesheetSerializer
from invoices.timesheet import JobPosition, Timesheet, Employee


class TimesheetTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(TimesheetTestCase, self).setUp()
        self.model_name = 'timesheet'
        self.model = Timesheet
        self.serializer = TimesheetSerializer

        date = datetime.now()
        jobposition = JobPosition.objects.create(name='name 0')
        employee = Employee.objects.create(user=self.user,
                                           start_contract=date,
                                           occupation=jobposition)

        self.items = [self.model.objects.create(start_date=date,
                                                employee=employee,
                                                end_date=date),
                      self.model.objects.create(start_date=date,
                                                employee=employee,
                                                end_date=date),
                      self.model.objects.create(start_date=date,
                                                employee=employee,
                                                end_date=date),

                      self.model.objects.create(start_date=date,
                                                employee=employee,
                                                end_date=date)]

        self.valid_payload = {
            'start_date': date.strftime('%Y-%m-%d'),
            'employee': employee.id,
            'end_date': date.strftime('%Y-%m-%d')
        }

        self.invalid_payload = {
            'employee': '',
            'start_date': date.strftime('%Y-%m-%d')
        }
