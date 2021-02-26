from auditlog.registry import auditlog
from colorfield.fields import ColorField
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import pre_save, post_delete, post_save
from django.dispatch import receiver

from invoices.storages import CustomizedGoogleDriveStorage


class JobPosition(models.Model):
    class Meta:
        ordering = ['-id']

    name = models.CharField(max_length=50)
    description = models.TextField(max_length=100, blank=True,
                                   null=True)

    def __str__(self):
        return '%s' % (self.name.strip())


class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    start_contract = models.DateField(u'start date')
    end_contract = models.DateField(u'end date', blank=True,
                                    null=True)
    provider_code = models.CharField(u'Provider code',
                                     help_text=u'Enter the service provider code at the C.N.S',
                                     max_length=30,
                                     blank=True)
    occupation = models.ForeignKey(JobPosition,
                                   on_delete=models.CASCADE)
    has_gdrive_access = models.BooleanField(u"Allow access to Google Drive files", default=False)
    has_gcalendar_access = models.BooleanField(u"Allow access to Prestations' calendar", default=False)
    driving_licence_number = models.CharField(u'Driver Licence Number',
                                              help_text=u'Enter the driver licence number',
                                              max_length=20,
                                              blank=True)
    abbreviation = models.CharField('Abbreviation',
                                    help_text='Enter employee abbreviation, must be unique accross company',
                                    max_length=3,
                                    default='XXX')
    color_cell = ColorField(default='#FF0000')
    color_text = ColorField(default='#FF0000')

    birth_place = models.CharField(u'Birth Place',
                                   help_text=u'Enter the City / Country of Birth',
                                   max_length=30,
                                   blank=True)

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
            message = u'User must have email to grant access'
            is_valid = False

        return is_valid, message

    @staticmethod
    def autocomplete_search_fields():
        return 'occupation__name', 'user__first_name', 'user__last_name', 'user__username'

    def __str__(self):
        return '%s (%s)' % (self.user.username.strip().capitalize(), self.abbreviation)


class EmployeeContractDetail(models.Model):
    start_date = models.DateField(u'Date début période')
    end_date = models.DateField(u'Date fin période', blank=True, null=True)
    number_of_hours = models.PositiveSmallIntegerField(u"Nombre d'heures par semaine",
                                                       validators=[MinValueValidator(5), MaxValueValidator(40)])
    employee_link = models.ForeignKey(Employee, on_delete=models.CASCADE)

    def calculate_current_daily_hours(self):
        return self.number_of_hours / 5

    def __str__(self):
        return u'Du %s au %s : %d heures/semaine' % (self.start_date, self.end_date, self.number_of_hours)


@receiver(pre_save, sender=User, dispatch_uid="user_pre_save_gservices_permissions")
def user_pre_save_gservices_permissions(sender, instance, **kwargs):
    from invoices.models import prestation_gcalendar
    from invoices.models import gd_storage
    try:
        origin_user = User.objects.filter(pk=instance.id).get()
        origin_email = origin_user.email
        email = instance.email
        if origin_email != email:
            has_access = False
            prestation_gcalendar.update_calendar_permissions(origin_email, has_access)
            path = CustomizedGoogleDriveStorage.MEDICAL_PRESCRIPTION_FOLDER
            gd_storage.update_folder_permissions_v3(path, origin_email, has_access)
            gd_storage.update_folder_permissions_v3(gd_storage.INVOICEITEM_BATCH_FOLDER, origin_email, has_access)
    except User.DoesNotExist:
        pass


@receiver(post_delete, sender=User, dispatch_uid="user_revoke_gservices_permissions")
def user_revoke_gservices_permissions(sender, instance, **kwargs):
    from invoices.models import prestation_gcalendar
    from invoices.models import gd_storage
    email = instance.email
    if email:
        has_access = False
        prestation_gcalendar.update_calendar_permissions(email, has_access)
        path = CustomizedGoogleDriveStorage.MEDICAL_PRESCRIPTION_FOLDER
        gd_storage.update_folder_permissions_v3(path, email, has_access)
        gd_storage.update_folder_permissions_v3(gd_storage.INVOICEITEM_BATCH_FOLDER, email, has_access)


@receiver([post_save, post_delete], sender=Employee, dispatch_uid="employee_update_gdrive_permissions")
def medical_prescription_clean_gdrive_post_delete(sender, instance, **kwargs):
    from invoices.models import gd_storage
    email = instance.user.email
    if email:
        path = CustomizedGoogleDriveStorage.MEDICAL_PRESCRIPTION_FOLDER
        has_access = instance.has_gdrive_access
        gd_storage.update_folder_permissions_v3(path, email, has_access)
        gd_storage.update_folder_permissions_v3(gd_storage.INVOICEITEM_BATCH_FOLDER, email, has_access)


@receiver(post_save, sender=Employee, dispatch_uid="employee_update_gcalendar_permissions")
def employee_update_gcalendar_permissions(sender, instance, **kwargs):
    from invoices.models import prestation_gcalendar
    email = instance.user.email
    if email:
        has_access = instance.has_gcalendar_access
        prestation_gcalendar.update_calendar_permissions(email, has_access)


@receiver(post_delete, sender=Employee, dispatch_uid="employee_revoke_gservices_permissions")
def employee_revoke_gservices_permissions(sender, instance, **kwargs):
    from invoices.models import prestation_gcalendar
    from invoices.models import gd_storage
    email = instance.user.email
    if email:
        has_access = False
        prestation_gcalendar.update_calendar_permissions(email, has_access)
        path = CustomizedGoogleDriveStorage.MEDICAL_PRESCRIPTION_FOLDER
        gd_storage.update_folder_permissions_v3(path, email, has_access)
        gd_storage.update_folder_permissions_v3(gd_storage.INVOICEITEM_BATCH_FOLDER, email, has_access)

auditlog.register(Employee)
