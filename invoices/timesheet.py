from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from invoices.storages import CustomizedGoogleDriveStorage
from django.core.exceptions import ValidationError


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
    has_gdrive_access = models.BooleanField("Allow access to Medical Prescriptions' scans", default=False)

    def clean(self, *args, **kwargs):
        super(Employee, self).clean()
        is_has_gdrive_access_valid, message = self.is_has_gdrive_access_valid(self.has_gdrive_access, self.user)
        if not is_has_gdrive_access_valid:
            raise ValidationError({'has_gdrive_access': message})

    @staticmethod
    def is_has_gdrive_access_valid(has_gdrive_access, user):
        is_valid = True
        message = ''
        if has_gdrive_access and not user.email:
            message = 'User must have email to grant access'
            is_valid = False

        return is_valid, message

    @staticmethod
    def autocomplete_search_fields():
        return 'occupation__name', 'user__first_name', 'user__last_name', 'user__username'

    def __unicode__(self):  # Python 3: def __str__(self):
        return '%s' % (self.user.username.strip())


@receiver([post_save, post_delete], sender=Employee, dispatch_uid="employee_update_gdrive_permissions")
def medical_prescription_clean_gdrive_post_delete(sender, instance, **kwargs):
    from invoices.models import gd_storage
    email = instance.user.email
    if email:
        path = CustomizedGoogleDriveStorage.MEDICAL_PRESCRIPTION_FOLDER
        has_access = instance.has_gdrive_access
        gd_storage.update_folder_permissions(path, email, has_access)


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

    @staticmethod
    def autocomplete_search_fields():
        return 'name'

    def __str__(self):  # Python 3: def __str__(self):
        return '%s' % (self.name.strip())


class TimesheetDetail(models.Model):
    start_date = models.DateTimeField('start date')
    end_date = models.DateTimeField('end date')
    task_description = models.ManyToManyField(TimesheetTask, help_text="Entrez une ou plusieurs taches.")
    patient = models.ForeignKey('invoices.Patient')
    timesheet = models.ForeignKey(Timesheet)
    other = models.CharField(max_length=50, blank=True,null=True)

    def __str__(self):  # Python 3: def __str__(self):
        return ''
