from django.db import models
from django.contrib.auth.models import User
from invoices.models import Patient

class JobPosition(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=100, blank=True,
                                   null=True)

    def __str__(self):  # Python 3: def __str__(self):
        return '%s' % (self.name.strip())


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    start_contract = models.DateField('start date')
    end_contract = models.DateField('end date', blank=True,
                                    null=True)
    occupation = models.ForeignKey(JobPosition)
    def __str__(self):  # Python 3: def __str__(self):
        return '%s' % (self.user.username.strip())


class Timesheet(models.Model):
    employee = models.ForeignKey(Employee)
    start_date = models.DateField('Date debut')
    start_date.editable = True
    end_date = models.DateField('Date fin')
    end_date.editable = True
    submitted_date = models.DateTimeField("Date d'envoi", blank=True,
                                     null=True)
    submitted_date.editable = True
    other_details = models.TextField("Autres details",max_length=100, blank=True,
                                     null=True)
    timesheet_validated = models.BooleanField("Valide", default=False)



class TimesheetTask(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=100, blank=True,
                                   null=True)
    def __str__(self):  # Python 3: def __str__(self):
        return '%s' % (self.name.strip())


class TimesheetDetail(models.Model):
    start_date = models.DateTimeField('start date')
    end_date = models.DateTimeField('end date')
    task_description = models.ManyToManyField(TimesheetTask, help_text="Entrez une ou plusieurs taches.")
    patient = models.ForeignKey(Patient)
    timesheet = models.ForeignKey(Timesheet)
    other = models.CharField(max_length=50, blank=True,null=True)

    def __str__(self):  # Python 3: def __str__(self):
        return ''
