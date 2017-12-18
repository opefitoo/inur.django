from api.tests.views.base import BaseTestCase
from rest_framework.test import APITestCase

from api.serializers import TimesheetTaskSerializer
from invoices.timesheet import TimesheetTask


class TimesheetTaskTestCase(BaseTestCase, APITestCase):
    def setUp(self):
        super(TimesheetTaskTestCase, self).setUp()
        self.model_name = 'timesheettask'
        self.model = TimesheetTask
        self.serializer = TimesheetTaskSerializer
        self.items = [self.model.objects.create(name='Some name0'),
                      self.model.objects.create(name='Some name1'),
                      self.model.objects.create(name='Some name2'),
                      self.model.objects.create(name='Some name3')]

        self.valid_payload = {
            'name': 'Some name4'
        }

        self.invalid_payload = {
            'name': ''
        }
