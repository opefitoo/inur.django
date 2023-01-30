import os

from colorfield.fields import ColorField
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import pre_save, post_delete, post_save
from django.dispatch import receiver
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

from invoices.enums.generic import GenderType
from invoices.enums.holidays import ContractType
from invoices.storages import CustomizedGoogleDriveStorage


def avatar_storage_location(instance, filename):
    file_name, file_extension = os.path.splitext(filename)
    if instance.start_contract is None:
        _current_yr_or_prscr_yr = now().date().strftime('%Y')
        _current_month_or_prscr_month = now().date().strftime('%M')
    else:
        _current_yr_or_prscr_yr = str(instance.start_contract.year)
        _current_month_or_prscr_month = str(instance.start_contract.month)
    path = os.path.join("Doc. Admin employes", "%s_%s" % (instance.user.last_name.upper(),
                                                          instance.user.first_name.capitalize()))
    filename = '%s_%s_%s_%s%s' % (
        _current_yr_or_prscr_yr, _current_month_or_prscr_month, instance.abbreviation,
        "avatar",
        file_extension)
    return os.path.join(path, filename)

def validate_avatar(file):
    try:
        file_size = file.file.size
    except:
        return
    limit_kb = 10
    if file_size > limit_kb * 1024 * 1024:
        raise ValidationError(_("Maximum file size is %s MB" % limit_kb))
class JobPosition(models.Model):
    class Meta:
        ordering = ['-id']

    name = models.CharField(max_length=50)
    description = models.TextField(max_length=100, blank=True,
                                   null=True)
    is_involved_in_health_care = models.BooleanField("Impliqué dans les soins", default=True)

    def __str__(self):
        return '%s' % (self.name.strip())

class Employee(models.Model):
    class Meta:
        ordering = ['-id']
    gender = models.CharField("Sex",
                              max_length=5,
                              choices=GenderType.choices,
                              default=None,
                              blank=True,
                              null=True
                              )
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
                                    help_text='Enter employee abbreviation, must be unique across company',
                                    max_length=3,
                                    default="XXX")
    phone_number = PhoneNumberField(blank=True)
    bank_account_number = models.CharField("Numéro de compte IBAN", help_text="Code BIC + IBAN",
                                           max_length=50, blank=True)
    address = models.TextField("Adresse", max_length=100, blank=True, null=True)
    access_card_number = models.CharField("Carte Voiture", max_length=20, blank=True, null=True)
    access_card_code = models.CharField("Code Carte Voiture", max_length=40, blank=True, null=True)
    sn_code = models.CharField("Matricule sécurité sociale", max_length=40, blank=True, null=True)
    end_trial_period = models.DateField("Fin période d'essai", blank=True, null=True)
    citizenship = CountryField(blank_label='...', blank=True, null=True)
    color_cell = ColorField(default='#FF0000')
    color_text = ColorField(default='#FF0000')
    birth_date = models.DateField(u'birth date', blank=True, null=True)

    birth_place = models.CharField(u'Birth Place',
                                   help_text=u'Enter the City / Country of Birth',
                                   max_length=50,
                                   blank=True)
    avatar = models.ImageField(upload_to=avatar_storage_location,
                               validators=[validate_avatar],
                               help_text=_("You can attach the scan of the declaration"),
                               null=True, blank=True)
    bio = models.TextField("Bio", default="Fill in your bio", max_length=200)
    to_be_published_on_www = models.BooleanField("Public Profile",
                                                 help_text="If checked then bio and avatar fields become mandatory",
                                                 blank=True, null=True)

    def get_current_contract(self):
        return self.contract_set.filter(end_date__isnull=True).first()
    def clean(self, *args, **kwargs):
        super(Employee, self).clean()
        is_has_gdrive_access_valid, message = self.is_has_gdrive_access_valid(self.has_gdrive_access, self.user)
        if not is_has_gdrive_access_valid:
            raise ValidationError({'has_gdrive_access': message})
        ## if self.address contains line breaks, replace them with spaces
        if self.address:
            self.address = self.address.replace('\n', ' ').replace('\r', '').replace('  ', ' ')
        ## if abbreviation is not unique, raise error, except if abbreviation is 'XXX'
        if self.abbreviation and self.abbreviation != 'XXX':
            if Employee.objects.filter(abbreviation=self.abbreviation).exclude(id=self.id).exists():
                raise ValidationError({'abbreviation': 'Abbreviation must be unique across company'})

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
        # return '%s (%s)' % (self.user.username.strip().capitalize(), self.abbreviation)
        return ' - '.join([self.user.username.strip().capitalize(), self.abbreviation])


def contract_storage_location(instance, filename):
    file_name, file_extension = os.path.splitext(filename)
    if instance.start_date:
        _current_yr_or_prscr_yr = instance.start_date.year
        _current_month_or_prscr_month = instance.start_date.month
    else:
        _current_yr_or_prscr_yr = str(instance.employee_link.start_contract.year)
        _current_month_or_prscr_month = str(instance.employee_link.start_contract.month)
    path = os.path.join("Doc. Admin employes", "%s_%s" % (instance.employee_link.user.last_name.upper(),
                                                          instance.employee_link.user.first_name.capitalize()))
    filename = '%s_%s_%s_%s%s' % (
        _current_yr_or_prscr_yr, _current_month_or_prscr_month, instance.employee_link.abbreviation,
        "contract", file_extension)
    return os.path.join(path, filename)
class EmployeeContractDetail(models.Model):
    start_date = models.DateField(u'Date début période')
    end_date = models.DateField(u'Date fin période', blank=True, null=True)
    number_of_hours = models.PositiveSmallIntegerField(u"Nombre d'heures par semaine",
                                                       validators=[MinValueValidator(5), MaxValueValidator(40)])
    contract_type = models.CharField("Type contrat",
                                     max_length=10,
                                     choices=ContractType.choices,
                                     default=ContractType.CDI, blank=True, null=True)
    monthly_wage = models.DecimalField("Salaire Mensuel", max_digits=8, decimal_places=2, blank=True, null=True)
    index = models.DecimalField("Index", max_digits=8, decimal_places=2, blank=True, null=True)
    number_of_days_holidays = models.PositiveSmallIntegerField(u"Nombre de jours de congés",
                                                               validators=[MinValueValidator(0),
                                                                           MaxValueValidator(36)])
    employee_link = models.ForeignKey(Employee, on_delete=models.CASCADE)
    employee_contract_file = models.FileField(upload_to=contract_storage_location,
                                              help_text=_("You can attach the scan of the contract"),
                                              null=True, blank=True)
    contract_signed_date = models.DateField(u'Date signature contrat', blank=True, null=True)
    contract_date = models.DateField(u'Date contrat', blank=True, null=True)
    employee_trial_period_text = models.TextField("Texte période d'essai", max_length=800, blank=True, null=True)
    employee_special_conditions_text = models.TextField("Texte conditions spéciales", max_length=200, blank=True, null=True)
    career_rank = models.CharField("Grade", max_length=10, blank=True, null=True)
    anniversary_career_rank = models.DateField(u'Date anniversaire grade', blank=True, null=True)

    def calculate_current_daily_hours(self):
        return self.number_of_hours / 5

    def __str__(self):
        if self.end_date:
            return u'Du %s au %s : %d heures/semaine' % (self.start_date, self.end_date, self.number_of_hours)
        return u'Du %s : %d heures/semaine' % (self.start_date, self.number_of_hours)


def update_filename(instance, filename):
    file_name, file_extension = os.path.splitext(filename)
    if instance.employee.start_contract is None:
        _current_yr_or_prscr_yr = now().date().strftime('%Y')
        _current_month_or_prscr_month = now().date().strftime('%M')
    else:
        _current_yr_or_prscr_yr = str(instance.employee.start_contract.year)
        _current_month_or_prscr_month = str(instance.employee.start_contract.month)
    path = os.path.join("Doc. Admin employes", "%s_%s" % (instance.employee.user.last_name.upper(),
                                                          instance.employee.user.first_name.capitalize()))
    filename = '%s_%s_%s_%s%s' % (
        _current_yr_or_prscr_yr, _current_month_or_prscr_month, instance.employee.abbreviation,
        instance.file_description,
        file_extension)
    return os.path.join(path, filename)


class EmployeeAdminFile(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    file_description = models.CharField("description", max_length=50)
    file_upload = models.FileField(null=True, blank=True, upload_to=update_filename)


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

