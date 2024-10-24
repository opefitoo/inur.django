import hashlib
import os

from colorfield.fields import ColorField
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField
from rest_framework.authtoken.models import Token

from invoices import settings
from invoices.actions.gcontacts import GoogleContacts
from invoices.enums.event import EventTypeEnum
from invoices.enums.generic import GenderType
from invoices.enums.holidays import ContractType


def get_employee_by_abbreviation(abbreviation):
    return Employee.objects.get(abbreviation=abbreviation)


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


def minified_avatar_storage_location(instance, filename):
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
        "minified_avatar",
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
    # job type is an enum of 3 choices:  soignant , administratif , logistique
    job_type = models.CharField("Type de poste",
                                max_length=20,
                                choices=[('soignant', _('Soignant')), ('administratif', _('Administratif')),
                                         ('logistique', _('Logistique'))],
                                default='soignant')
    is_involved_in_health_care = models.BooleanField("Impliqué dans les soins", default=True)

    def __str__(self):
        return '%s' % (self.name.strip())


class Employee(models.Model):
    class Meta:
        ordering = ['-end_contract', 'id']

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
    google_user_id = models.CharField(u'Google User ID', max_length=100, blank=True, null=True)
    driving_licence_number = models.CharField(u'Driver Licence Number',
                                              help_text=u'Enter the driver licence number',
                                              max_length=20,
                                              blank=True)
    abbreviation = models.CharField('Abbreviation',
                                    help_text='Enter employee abbreviation, must be unique across company',
                                    max_length=3,
                                    default="XXX")
    phone_number = PhoneNumberField(blank=True)
    additional_phone_number = PhoneNumberField(blank=True)
    personal_email = models.EmailField(blank=True)
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
    by_pass_shifts = models.BooleanField("Bypass shifts", default=False)

    birth_place = models.CharField(u'Birth Place',
                                   help_text=u'Enter the City / Country of Birth',
                                   max_length=50,
                                   blank=True)
    avatar = models.ImageField(upload_to=avatar_storage_location,
                               validators=[validate_avatar],
                               help_text=_("You can attach the scan of the declaration"),
                               null=True, blank=True)
    minified_avatar = models.ImageField(upload_to=minified_avatar_storage_location,
                                        validators=[validate_avatar],
                                        help_text=_("You can attach the minified version of the avatar"),
                                        null=True, blank=True)
    minified_avatar_base64 = models.TextField("Minified Avatar Base64 encoded", blank=True, null=True)
    bio = models.TextField("Bio", default="Fill in your bio", max_length=200)
    to_be_published_on_www = models.BooleanField("Public Profile",
                                                 help_text="If checked then bio and avatar fields become mandatory",
                                                 blank=True, null=True)
    virtual_career_anniversary_date = models.DateField("Date anniversaire carrière virtuelle",
                                                       help_text="Pour les carrières sous convention SAS",
                                                       blank=True, null=True)
    miscellaneous = models.TextField("Divers", default="Code Pin tél:...etc", max_length=200)

    def get_current_contract(self):
        return EmployeeContractDetail.objects.filter(employee_link=self, end_date__isnull=True).get()

    @property
    def get_link_to_holiday_requests(self):
        return mark_safe('<a href="%s?employee__id__exact=%s">Voir les demandes de congés</a>' % (
            reverse("admin:invoices_holidayrequest_changelist"), self.user.id))

    @property
    def employee_fte(self):
        if self.end_contract:
            return 0
        else:
            return self.get_current_contract().number_of_hours / 40

    @property
    def calculate_age(self):
        if self.birth_date:
            return now().year - self.birth_date.year
        else:
            return None

    @property
    def total_number_of_un_validated_events(self):
        from dependence.stats.employee_stats import get_un_validated_events, get_validated_events
        unvalidated_events = get_un_validated_events(self.id)
        validated_events = get_validated_events(self.id)
        url = f'{reverse("admin:invoices_eventlist_changelist")}?id__in={",".join([str(event.id) for event in unvalidated_events])}'
        # calculate ratio = unvalidated_events.count() / validated_events.count() in percentage
        ratio = 0
        if validated_events.count() > 0:
            ratio = unvalidated_events.count() / validated_events.count() * 100
        else:
            ratio = 100
        return mark_safe(
            '<a href="%s">%s</a>' % (
            url, "%d / %d (%d %%)" % (unvalidated_events.count(), validated_events.count(), ratio)))

    @property
    def age_group(self):
        age = self.calculate_age
        if age is None:
            return "N/A"
        # per age group 0-10, 11-20, 21-30, 31-40, 41-50, 51-60, 61-70, 71+
        if age < 11:
            return "0-10"
        if age < 21:
            return "11-20"
        if age < 31:
            return "21-30"
        if age < 41:
            return "31-40"
        if age < 51:
            return "41-50"
        if age < 61:
            return "51-60"
        if age < 71:
            return "61-70"
        return "71+"

    @property
    def is_involved_in_health_care(self):
        return self.occupation.is_involved_in_health_care

    def get_contrat_at_date(self, date):
        print("get_current_contract for %s and ID: %s" % (self.user, self.id))
        # start_date__lte=date and end_date__gte date or end_date__isnull = True use | Q(end_date__isnull=True)
        details = EmployeeContractDetail.objects.filter(Q(employee_link=self) & (
                Q(start_date__lte=date) & (Q(end_date__gte=date) | Q(end_date__isnull=True)))).order_by('-id')
        if details:
            return details[0]
        else:
            return None

    def send_email_with_events(self, text, date_planning):
        # send email text to employee
        employee_email = self.personal_email
        admin_email = Employee.objects.get(id=1).user.email
        # send email to employee
        to_emails = [self.user.email, employee_email, admin_email]
        # format date to french only DD-MM-YYYY
        date_planning = date_planning.strftime('%d-%m-%Y')
        from invoices.notifications import send_email_notification
        send_email_notification(u'Programme de la journée du %s' % date_planning,
                                'Bonjour %s, Voici le planning du %s \n%s' % (
                                self.user.first_name, date_planning, text),
                                to_emails)

    def get_contracts_between_dates(self, start_date, end_date):
        return self.employeecontractdetail_set.filter(
            Q(start_date__lte=end_date, end_date__gte=start_date) |
            Q(start_date__lte=end_date, end_date__isnull=True)
        ).exclude(start_date__gt=end_date, end_date__lt=start_date)

        # other fields...

    def get_average_hours_per_week(self, start_date, end_date):
        contracts = self.get_contracts_between_dates(start_date, end_date)
        total_hours = 0
        total_weeks = 0

        # Sort contracts by start_date
        contracts = sorted(contracts, key=lambda x: x.start_date)

        # Initialize the previous contract end date as the start_date
        prev_contract_end = start_date

        for contract in contracts:
            # If there's a gap between the previous contract end date and the current contract start date,
            # consider the number of hours for that period as 0
            if contract.start_date > prev_contract_end:
                gap_weeks = (contract.start_date - prev_contract_end).days / 7
                total_weeks += gap_weeks

            contract_start = max(contract.start_date, start_date)
            contract_end = min(contract.end_date or end_date, end_date)
            weeks = (contract_end - contract_start).days / 7
            total_hours += contract.number_of_hours * weeks
            total_weeks += weeks

            # Update the previous contract end date
            prev_contract_end = contract.end_date or end_date

        # If there's a gap between the last contract end date and the end_date,
        # consider the number of hours for that period as 0
        if end_date > prev_contract_end:
            gap_weeks = (end_date - prev_contract_end).days / 7
            total_weeks += gap_weeks

        if total_weeks == 0:
            return 0

        return round(total_hours / total_weeks, 2)

    def clean(self, *args, **kwargs):
        super(Employee, self).clean()
        ## if self.address contains line breaks, replace them with spaces
        if self.address:
            self.address = self.address.replace('\n', ' ').replace('\r', '').replace('  ', ' ')
        ## if abbreviation is not unique, raise error, except if abbreviation is 'XXX'
        if self.abbreviation and self.abbreviation != 'XXX':
            if Employee.objects.filter(abbreviation=self.abbreviation).exclude(id=self.id).exists():
                raise ValidationError({'abbreviation': 'Abbreviation must be unique across company'})
        # call validate_unique_phone_number
        self.validate_unique_phone_number()

    # validate that phone_number is unique
    def validate_unique_phone_number(self, exclude=None):
        super(Employee, self).validate_unique(exclude)
        if Employee.objects.filter(phone_number=self.phone_number).exclude(id=self.id).exists():
            raise ValidationError({'phone_number': 'Phone number must be unique across company'})

    def get_occupation(self):
        return self.occupation.name

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

    def delete_all_contacts_in_group(self, group_name):
        google_contacts = GoogleContacts(email=self.user.email)
        group_id = google_contacts.get_group_id_by_name(group_name)
        if group_id:
            contacts = google_contacts.get_contacts_in_group(group_id)
            print(f"Deleting {len(contacts)} contacts in group {group_name}...")
            google_contacts.batch_delete_contacts(contacts)
        else:
            print(f"Group {group_name} not found.")

    def sync_google_contacts(self):
        google_contacts = GoogleContacts(email=self.user.email)
        from invoices.models import Patient
        # get 10 first patients that are still alive
        patients_still_alive = Patient.objects.filter(date_of_death__isnull=True).order_by('-id')
        google_contacts.batch_create_new_patients(patients_still_alive)
        employees_who_still_work = Employee.objects.filter(end_contract__isnull=True).order_by('-id')
        for employee in employees_who_still_work:
            google_contacts.create_new_employee(employee)
        patients_passed_away = Patient.objects.filter(date_of_death__isnull=False).order_by('-id')
        for patient in patients_passed_away:
            google_contacts.delete_patient(patient)
        employees_who_left = Employee.objects.filter(end_contract__isnull=False).order_by('-id')
        for employee in employees_who_left:
            google_contacts.delete_employee(employee)

    def generate_unique_hash(self):
        # Concatenate the name and first_name
        combined_string = self.user.last_name + self.user.first_name + str(self.id)

        # Create a SHA256 hash
        result = hashlib.sha256(combined_string.encode())

        # Return the hexadecimal string
        return result.hexdigest()

    def __str__(self):
        # return '%s (%s)' % (self.user.username.strip().capitalize(), self.abbreviation)
        return ' - '.join([self.user.username.strip().capitalize(), self.abbreviation])


class Shift(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g., 'Morning', 'Night'
    start_time = models.TimeField()
    end_time = models.TimeField()

    # name should be unique.

    def __str__(self):
        return self.name


class EmployeeShift(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE)
    date = models.DateField()

    def __str__(self):
        return f"{self.employee.name} - {self.shift.name} on {self.date}"


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
    index = models.PositiveIntegerField("Index", blank=True, null=True)
    responsibility_bonus = models.PositiveIntegerField("Index", blank=True, null=True)
    number_of_days_holidays = models.PositiveSmallIntegerField(u"Nombre de jours de congés",
                                                               validators=[MinValueValidator(0),
                                                                           MaxValueValidator(37)])
    employee_link = models.ForeignKey(Employee, on_delete=models.CASCADE)
    employee_contract_file = models.FileField(upload_to=contract_storage_location,
                                              help_text=_("You can attach the scan of the contract"),
                                              null=True, blank=True)
    contract_signed_date = models.DateField(u'Date signature contrat', blank=True, null=True)
    contract_date = models.DateField(u'Date contrat', blank=True, null=True)
    employee_trial_period_text = models.TextField("Texte période d'essai", max_length=800, blank=True, null=True)
    employee_special_conditions_text = models.TextField("Texte conditions spéciales", max_length=200, blank=True,
                                                        null=True)
    career_rank = models.CharField("Grade", help_text="Sous format Grade / Ancienneté Carrière", max_length=10,
                                   blank=True, null=True)
    anniversary_career_rank = models.DateField(u'Date anniversaire grade', blank=True, null=True)
    weekly_work_organization = models.TextField("Organisation du travail hebdomadaire",
                                                help_text="Veuillez saisir ce champ sous format: 8h/j 5 jours par semaine",
                                                max_length=80, blank=True, null=True)

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
    file_description = models.CharField("description", max_length=60)
    document_expiry_date = models.DateField(u'Date d\'expiration du document', blank=True, null=True)
    file_upload = models.FileField(null=True, blank=True, upload_to=update_filename)


class Training(models.Model):
    name = models.CharField("Nom de la formation", max_length=100)
    description = models.TextField("Description de la formation", max_length=200)
    # can be followed remotely
    remote = models.BooleanField("Formation à distance", default=False)
    training_location = models.TextField("Lieu de la formation", max_length=500, blank=True, null=True)
    training_cost = models.DecimalField("Coût de la formation", max_digits=8, decimal_places=2,
                                        blank=True, null=True)
    # meta
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # verbose name
    class Meta:
        verbose_name = "Formation"
        verbose_name_plural = "Formations"

    def __str__(self):
        return self.name


# a model that will store the training dates and times, a training can have multiple dates and times
class TrainingDates(models.Model):
    training = models.ForeignKey(Training, on_delete=models.CASCADE)
    training_start_date_time = models.DateTimeField(u'Date de début de la formation')
    training_end_date_time = models.DateTimeField(u'Date de fin de la formation')

    def __str__(self):
        return f"{self.training.name} - {self.training_start_date_time} - {self.training_end_date_time}"

    def create_or_update_event_for_training_date(self, employee):
        from invoices.events import Event, EventGenericLink
        training_event = Event.objects.filter(day=self.training_start_date_time.date(),
                                              time_start_event=self.training_start_date_time.time(),
                                              time_end_event=self.training_end_date_time.time(),
                                              event_type_enum=EventTypeEnum.EMPL_TRNG,
                                              employees=employee).first()
        if training_event:
            training_event.update(title=self.training.name,
                                  start_date=self.training_start_date_time,
                                  end_date=self.training_end_date_time)
        else:
            training_event = Event.objects.create(
                day=self.training_start_date_time.date(),
                time_start_event=self.training_start_date_time.time(),
                time_end_event=self.training_end_date_time.time(),
                event_type_enum=EventTypeEnum.EMPL_TRNG,
                state=2,
                event_address=self.training.training_location if self.training.training_location else 'lieu de formation non défini',
                notes='Formation %s' % self.training.name,
                employees=employee,
                created_by='when crud training'
            )

            event_generic_link = EventGenericLink.objects.create(
                event=training_event,
                content_type=ContentType.objects.get_for_model(self),
                object_id=self.id
            )
            return training_event

    def delete_event_for_training_date(self, employee):
        # find event through event_generic_link
        from invoices.events import Event, EventGenericLink

        event_generic_link = EventGenericLink.objects.filter(content_type=ContentType.objects.get_for_model(self),
                                                             object_id=self.id).first()
        if event_generic_link:
            event = Event.objects.filter(id=event_generic_link.event.id).first()
            if event:
                event.delete()



class EmployeeTraining(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    training_link = models.ForeignKey(Training, on_delete=models.CASCADE)
    training_certificate = models.FileField(null=True, blank=True, upload_to="training_certificates/")
    training_completed_date = models.DateField(u'Date de fin de la formation', blank=True, null=True)
    training_success = models.BooleanField("Formation réussie", default=False)
    training_paid_by_company = models.BooleanField("Formation payée par l'entreprise", default=False)

    def _create_or_update_events_for_trainings(self):
        training_dates = TrainingDates.objects.filter(training=self.training_link)
        for training_date in training_dates:
            # create or update event for this training date
            training_date.create_or_update_event_for_training_date(employee=self.employee)

    def _delete_events_for_trainings(self):
        training_dates = TrainingDates.objects.filter(training=self.training_link)
        for training_date in training_dates:
            # create or update event for this training date
            training_date.delete_event_for_training_date(employee=self.employee)

    def __str__(self):
        return f"{self.employee} - {self.training_link} - {self.training_completed_date}"
    # validate that dates


class EmployeeProxy(Employee):
    class Meta:
        proxy = True
        # verbose_name = "XXX"
        # verbose_name_plural = "XXXs"


@receiver(post_save, sender=Employee, dispatch_uid='create_auth_token')
def create_auth_token(sender, instance=None, created=False, **kwargs):
    # if in test mode, do not create token
    if settings.TESTING:
        print("** TEST mode ** will not create token")
        return
    if instance.end_contract:
        instance.user.is_active = False
        instance.user.save()
        # delete token if exists
        if Token.objects.filter(user=instance.user).exists():
            Token.objects.filter(user=instance.user).delete()
    elif created or (not Token.objects.filter(user=instance.user).exists() and instance.end_contract is None):
        instance.user.is_active = True
        instance.user.save()
        Token.objects.create(user=instance.user)


@receiver(post_save, sender=EmployeeTraining, dispatch_uid='create_or_update_employees_events_for_trainings')
def create_or_update_employees_events_for_trainings(sender, instance=None, created=False, **kwargs):
    if instance and instance.employee.end_contract is None:
        from invoices.processors.tasks import create_or_update_events_for_trainings_task
        # if used in local development, do not use celery
        if os.environ.get('LOCAL_ENV', None):
            create_or_update_events_for_trainings_task(instance)
            return None
        create_or_update_events_for_trainings_task.delay(instance)

@receiver(post_delete, sender=EmployeeTraining, dispatch_uid='delete_employees_events_for_trainings')
def delete_employees_events_for_trainings(sender, instance=None, **kwargs):
    if instance and instance.employee.end_contract is None:
        from invoices.processors.tasks import delete_events_for_trainings_task
        # if used in local development, do not use celery
        if os.environ.get('LOCAL_ENV', None):
            delete_events_for_trainings_task(instance)
            return None
        delete_events_for_trainings_task.delay(instance)


@receiver(post_save, sender=Employee, dispatch_uid='create_or_update_google_contact')
def create_or_update_google_contact(sender, instance=None, created=False, **kwargs):
    # if in test mode, do not create token
    if settings.TESTING:
        print("** TEST mode ** will not sync google contacts")
        return
    if instance and instance.end_contract is None:
        from invoices.processors.tasks import sync_google_contacts_for_single_employee as sync_google_contacts_task
        employees = Employee.objects.get(id=instance.id)
        if os.environ.get('SKIP_GOOGLE_SYNCS', None):
            print("Skipping google syncs")
            return
        sync_google_contacts_task.delay(employees)
