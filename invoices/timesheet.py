from django.db import models
from django.contrib.auth.models import User
from models import Patient

class JobPosition(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=100, blank=True,
                                   null=True)

    def __unicode__(self):  # Python 3: def __str__(self):
        return '%s' % (self.name.strip())


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    start_contract = models.DateField('start date')
    end_contract = models.DateField('end date', blank=True,
                                    null=True)
    occupation = models.ForeignKey(JobPosition)


class Timesheet(models.Model):
    employee = models.ForeignKey(Employee)
    start_date = models.DateField('Timesheet start date')
    end_date = models.DateField('Timesheet end date')
    submitted_date = models.DateTimeField('submitted date')
    other_details = models.TextField(max_length=100, blank=True,
                                     null=True)

class TimesheetDetail(models.Model):
    start_date = models.DateTimeField('start date')
    end_date = models.DateTimeField('end date')
    task_description = models.CharField(max_length=30)
    patient = models.ForeignKey(Patient)
    timesheet = models.ForeignKey(Timesheet)