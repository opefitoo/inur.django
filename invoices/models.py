# -*- coding: utf-8 -*-
import base64
import logging
import os
import uuid
from copy import deepcopy
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.files.images import ImageFile
from django.core.files.storage import default_storage
from django.db import models
from django.db.models import Q, IntegerField, Max
from django.db.models.functions import Cast
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.utils.timezone import now
from django_countries.fields import CountryField
from pdf2image import convert_from_bytes
from phonenumber_field.modelfields import PhoneNumberField

from invoices.actions.gcontacts import GoogleContacts, async_delete_patient, async_create_or_update_new_patient
from invoices.actions.helpers import invoice_itembatch_medical_prescription_filename, invoice_itembatch_prefac_filename, \
    invoice_itembatch_ordo_filename, update_bedsore_pictures_filenames
from invoices.employee import Employee
from invoices.enums.generic import GenderType, BatchTypeChoices
from invoices.enums.medical import BedsoreEvolutionStatus
from invoices.modelspackage import InvoicingDetails
from invoices.processors.tasks import process_post_save, update_events_address
from invoices.validators.validators import MyRegexValidator
from invoices.xero.utils import get_xero_token, ensure_sub_contractor_contact_exists

# else:
#    gd_storage = FileSystemStorage()

logger = logging.getLogger(__name__)


class CareCode(models.Model):
    class Meta:
        ordering = ['-id']

    code = models.CharField(max_length=30, unique=True)
    name = models.TextField(max_length=320)
    description = models.TextField(max_length=400)
    reimbursed = models.BooleanField("Prise en charge par CNS", default=True)
    contribution_undue = models.BooleanField(u"Participation forfaitaire non dûe",
                                             help_text=u"Si vous sélectionnez cette option la participation de 12% ne "
                                                       u"sera pas déduite de cette prestation",
                                             default=False)
    is_package = models.BooleanField("Forfait", default=False,
                                     help_text="Si vous sélectionnez cette option, cela signifie que cette prestation est un forfait et que le prix est fixe")
    exclusive_care_codes = models.ManyToManyField("self", blank=True)

    @property
    def current_gross_amount(self):
        return self.gross_amount(datetime.date.today())

    def gross_amount(self, date):
        for v in self.validity_dates.all():
            if date.date() >= v.start_date:
                if v.end_date is None:
                    return v.gross_amount
                elif date.date() <= v.end_date:
                    return v.gross_amount
        return 0

    def gross_amount_date_based(self, date):
        if date is None:
            return 0
        if self.validity_dates.count() == 0:
            return 0
        for v in self.validity_dates.all():
            if date >= v.start_date:
                if v.end_date is None:
                    return v.gross_amount
                elif date <= v.end_date:
                    return v.gross_amount
        return 0

    def net_amount(self, date, private_patient, participation_statutaire):
        if not private_patient:
            if self.reimbursed and not self.contribution_undue:
                return round(((self.gross_amount(date) * 88) / 100), 2) + self._fin_part(date,
                                                                                         participation_statutaire=participation_statutaire)
            else:
                return self.gross_amount(date)
        else:
            return 0

    def _fin_part(self, date, participation_statutaire):
        "Returns the financial participation of the client"
        if participation_statutaire:
            return 0
        # round to only two decimals
        return round(((self.gross_amount(date) * 12) / 100), 2)
    @property
    def latest_price(self):
        return self.validity_dates.latest('start_date')

    def __str__(self):
        return '%s:%s' % (self.code, self.name)

    @staticmethod
    def autocomplete_search_fields():
        return 'name', 'code'

    def clean(self, *args, **kwargs):
        super(CareCode, self).clean_fields()
        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(CareCode.validate_combination(data))
        return result

    @staticmethod
    def validate_combination(data):
        messages = {}
        if 'contribution_undue' in data and data['contribution_undue'] is not None:
            is_invalid = data['reimbursed'] is False and data['contribution_undue'] is True
            if is_invalid:
                messages = {'contribution_undue':
                                u'Vous ne pouvez appliquer ce champ que pour les soins remboursés par la CNS'}
        return messages


class ValidityDate(models.Model):
    """
    CareCode cannot have start and end validity dates that overlap.
    Depending on Prestation date, gross_amount that is calculated in Invoice will differ.

    """

    class Meta:
        ordering = ['-start_date']

    start_date = models.DateField("date debut validite")
    end_date = models.DateField("date fin validite", blank=True, null=True)
    gross_amount = models.DecimalField("montant brut", max_digits=10, decimal_places=6)
    care_code = models.ForeignKey(CareCode
                                  , related_name='validity_dates'
                                  , on_delete=models.CASCADE)

    def __str__(self):
        if self.end_date is None:
            return 'from %s : %s EUR' % (self.start_date, round(self.gross_amount, 2))
        return 'from %s to %s : %s EUR' % (self.start_date, self.end_date, round(self.gross_amount, 2))

    def clean(self, *args, **kwargs):
        exclude = []
        if self.care_code is not None and self.care_code.id is None:
            exclude = ['care_code']

        super(ValidityDate, self).clean_fields(exclude)
        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(ValidityDate.validate_dates(data))

        return result

    @staticmethod
    def validate_dates(data):
        messages = {}
        is_valid = data['end_date'] is None or data['start_date'] <= data['end_date']
        if not is_valid:
            messages = {'end_date': 'End date must be bigger than Start date'}

        return messages


def extract_birth_date(code_sn) -> object:
    stripped_sn_code = code_sn.replace(" ", "")
    if stripped_sn_code is not None and (stripped_sn_code[:4]).isdigit():
        if (stripped_sn_code[4:6]).isdigit() and int(stripped_sn_code[4:6]) < 13:
            if (stripped_sn_code[6:8]).isdigit() and int(stripped_sn_code[6:8]) < 32:
                return datetime.strptime(stripped_sn_code[:8], '%Y%m%d')
    return None


def extract_birth_date_fr(code_sn) -> str:
    return datetime.strftime(extract_birth_date(code_sn), "%d/%m/%Y")


def extract_birth_date_iso(code_sn) -> str:
    return datetime.strftime(extract_birth_date(code_sn), '%Y-%m-%d')


def calculate_age(care_date, code_sn):
    if care_date is None:
        care_date = datetime.now()
    born = extract_birth_date(code_sn)
    if born is not None:
        return care_date.year - born.year - ((care_date.month, care_date.day) < (born.month, born.day))
    return None


# TODO: 1. can maybe be extending common class with Patient ?
# TODO: 2. synchronize physician details with Google contacts
class Physician(models.Model):
    class Meta:
        ordering = ['-id']

    provider_code = models.CharField(max_length=30)
    first_name = models.CharField(max_length=30)
    name = models.CharField(max_length=30)
    physician_speciality = models.CharField(max_length=30, blank=True, null=True, default=None)
    address = models.TextField(max_length=30)
    zipcode = models.CharField(max_length=10)
    city = models.CharField(max_length=30)
    country = CountryField(blank_label='...', blank=True, null=True)
    phone_number = models.CharField(max_length=30)
    fax_number = models.CharField(max_length=30, blank=True, null=True)
    email_address = models.EmailField(default=None, blank=True, null=True)

    @staticmethod
    def autocomplete_search_fields():
        return 'name', 'first_name'

    def __str__(self):  # Python 3: def __str__(self):
        return '%s %s' % (self.name.strip(), self.first_name.strip())

class SubContractor(models.Model):
    # SubContractor fields (like name, address, etc.)
    name = models.CharField(max_length=255)
    address = models.TextField(max_length=255)
    zipcode = models.CharField(max_length=10)
    city = models.CharField(max_length=30)
    country = CountryField(blank_label='...', blank=True, null=True)
    phone_number = models.CharField(max_length=30)
    fax_number = models.CharField(max_length=30, blank=True, null=True)
    email_address = models.EmailField(default=None, blank=True, null=True)
    provider_code = models.CharField("Code Prestataire", max_length=30, blank=True, null=True)
    billing_retrocession = models.DecimalField("Rétrocession facturation",
                                               max_digits=10,
                                               decimal_places=2, default=15)
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def create_subcontractor_in_xero(self):
        token = get_xero_token()

        headers = {
            'Authorization': f'Bearer {token.access_token}',
            'Content-Type': 'application/json'
        }
        response = requests.get('https://api.xero.com/connections', headers=headers)
        tenants = response.json()
        print("tenants: ", tenants)

        invoicing_details = InvoicingDetails.objects.get(default_invoicing=True)

        if invoicing_details.xero_tenant_id is None:
            raise Exception("No xero_tenant_id for invoice_details: ", invoicing_details)

        contact = ensure_sub_contractor_contact_exists(token.access_token,
                                        invoicing_details.xero_tenant_id,
                                        self)
        return contact


    def __str__(self):
        return self.name


class SubContractorAdminFile(models.Model):
    subcontractor = models.ForeignKey(SubContractor, on_delete=models.CASCADE)
    file = models.FileField(upload_to='subcontractor_files/')
    description = models.TextField()

    def __str__(self):
        return f"{self.subcontractor.name} - {self.description}"


# TODO: synchronize patient details with Google contacts
class Patient(models.Model):
    class Meta:
        ordering = ['-id']

    code_sn = models.CharField(max_length=30, validators=[MyRegexValidator(
        regex='^[12]\d{12}',
        message='Premier chiffre (1 à 2) suivi de 12 chiffres (0 à 9)',
        code='invalid_code_sn'
    ),
    ])
    first_name = models.CharField(max_length=30)
    name = models.CharField(max_length=30)
    gender = models.CharField("Sex",
                              max_length=5,
                              choices=GenderType.choices,
                              default=None,
                              blank=True,
                              null=True
                              )
    address = models.TextField(max_length=255)
    zipcode = models.CharField(max_length=10)
    city = models.CharField(max_length=30)
    country = CountryField(blank_label='...', blank=True, null=True)
    phone_number = models.CharField(max_length=30)
    additional_phone_number = PhoneNumberField("Numéro de tél. additionel", blank=True, null=True)
    email_address = models.EmailField(default=None, blank=True, null=True)
    participation_statutaire = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    is_under_dependence_insurance = models.BooleanField(u"Assurance dépendance", default=False)
    # date sortie de notre réseau
    date_of_exit = models.DateField(u"Date de sortie", default=None, blank=True, null=True)
    is_eligible_to_parameter_surveillance = models.BooleanField(u"Suivre Paramètres", default=False)
    date_of_death = models.DateField(u"Date de décès", default=None, blank=True, null=True)
    additional_details = models.TextField(u"Détails additionels",
                                          help_text="Vous pouvez mettre par exemple les numéros de carte adapto ou tout autre info utile.",
                                          max_length=500,
                                          default=None, blank=True, null=True)
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    @property
    def full_address(self):
        # if country is luxembourg then append L- to zip code if not already there
        if self.country == 'LU' or self.country is None:
            if self.zipcode[:2] != 'L-':
                self.zipcode = 'L-' + self.zipcode
        return "%s %s %s, %s" % (self.address, self.zipcode, self.city, self.country)

    def get_full_address_date_based(self, current_date=now().date(), current_time=now().time()):
        # gets the address where start_date is less than or equal to current_date
        # and (end_date is greater than current_date or end_date is None)
        # take into account that we have now start_time and end_time
        address = self.addresses.filter(start_date__lte=current_date).filter(
            Q(end_date__gte=current_date) | Q(end_date__isnull=True)).filter(
            Q(start_time__lte=current_time) | Q(start_time__isnull=True)).filter(
            Q(end_time__gte=current_time) | Q(end_time__isnull=True)).first()

        return address.full_address if address else self.full_address

    def addresses(self):
        return self.addresses.all().order_by('-start_date')

    @property
    def age(self):
        return self.calculate_age(None)

    @staticmethod
    def autocomplete_search_fields():
        return 'name', 'first_name'

    def birth_date(self):
        return extract_birth_date_fr(self.code_sn)

    def birth_date_as_object(self):
        return extract_birth_date(self.code_sn)

    def clean_phone_number(self):
        return self.phone_number.replace(" ", ".")

    def __str__(self):  # Python 3: def __str__(self):,
        return '%s %s' % (self.name.strip(), self.first_name.strip())

    def clean(self, *args, **kwargs):
        self.code_sn = self.format_code_sn(self.code_sn)
        super(Patient, self).clean_fields()
        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def format_code_sn(code_sn):
        return code_sn.replace(" ", "")

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(Patient.validate_code_sn(instance_id, data))
        result.update(Patient.validate_date_of_death(instance_id, data))
        result.update(Patient.patient_age_validation(data))
        return result

    @staticmethod
    def validate_date_of_death(instance_id, data):
        messages = {}
        if 'date_of_death' in data and data['date_of_death'] is not None:
            if Prestation.objects.filter(date__gte=data['date_of_death'], invoice_item__patient_id=instance_id).count():
                messages = {'date_of_death': 'Prestation for a later date exists'}

            if Hospitalization.objects.filter(end_date__gt=data['date_of_death'], patient_id=instance_id).count():
                messages = {'date_of_death': 'Hospitalization that ends later exists like for example %s' % Hospitalization.objects.filter(end_date__gte=data['date_of_death'], patient_id=instance_id).first()}

        return messages

    @staticmethod
    def validate_code_sn(instance_id, data):
        messages = {}
        if 'is_private' in data and not data['is_private']:
            code_sn = data['code_sn'].replace(" ", "")
            if Patient.objects.filter(code_sn=code_sn).exclude(pk=instance_id).count() > 0:
                messages = {'code_sn': 'Code SN must be unique'}
        return messages

    @staticmethod
    def patient_age_validation(data):
        messages = {}
        patient_age = calculate_age(None, data['code_sn'])
        if 'is_private' in data and not data['is_private']:
            if patient_age is None:
                messages = {'code_sn': 'Code SN does not look ok, if not private patient it should follow CNS scheme'}
            elif patient_age < 1 or patient_age > 120:
                messages = {'code_sn': 'Code SN does not look ok, patient cannot be %d year(s) old' % patient_age}
        return messages

    def calculate_age(self, care_date: object) -> object:
        return calculate_age(care_date, self.code_sn)

    def extract_birth_date(self) -> object:
        return self.extract_birth_date(self.code_sn)

    def clean_name(self):
        return self.cleaned_data['name'].upper()

    def clean_first_name(self):
        return self.cleaned_data['first_name'].capitalize()

    def bedsore_count(self):
        if self.id:
            return Bedsore.objects.filter(patient_id=self.id).count()
        return 0

    def fall_count(self):
        if self.id:
            from dependence.falldeclaration import FallDeclaration
            return FallDeclaration.objects.filter(patient_id=self.id).count()
        return 0

class PatientSubContractorRelationship(models.Model):
    RELATIONSHIP_TYPE_CHOICES = [
        ('contractor', 'We are Sub-Contractor'),
        ('main_company', 'We are Main Company'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    subcontractor = models.ForeignKey(SubContractor, on_delete=models.CASCADE)
    relationship_type = models.CharField(max_length=50, choices=RELATIONSHIP_TYPE_CHOICES)

    def __str__(self):
        return f"{self.patient.name} - {self.subcontractor.name} ({self.get_relationship_type_display()})"

class Bedsore(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    identification_date = models.DateField()
    location = models.CharField(max_length=255, help_text="Exemple: Dos, Talon droit, etc.")
    # bedsore origin can be liée à la prise en charge  ou non liée à la prise en charge
    is_linked_to_care = models.BooleanField(default=True,
                                            help_text="Si vous sélectionnez cette option, cela signifie que l'escarre est liée à la prise en charge")
    initial_description = models.TextField()  # Description initiale de l'escarre

    def __str__(self):  # Python 3: def __str__(self):
        return 'Escarre de %s datant de %s sur "%s"' % (self.patient, self.identification_date, self.location)

    class Meta:
        ordering = ['-identification_date']
        verbose_name = "Escarre"
        verbose_name_plural = "Escarres"


def validate_image(image):
    try:
        file_size = image.file.size
    except:
        return
    limit_kb = 10
    if file_size > limit_kb * 1024 * 1024:
        raise ValidationError("Taille maximale du fichier est %s MO" % limit_kb)


class BedsoreEvaluation(models.Model):
    bedsore = models.ForeignKey(Bedsore, on_delete=models.CASCADE)
    evaluation_date = models.DateField()
    stage = models.IntegerField(choices=[(1, 'Stage 1'), (2, 'Stage 2'), (3, 'Stage 3'), (4, 'Stage 4')])
    size = models.DecimalField(verbose_name="Taille en cm", max_digits=5, decimal_places=2)  # Size in cm² for example
    depth = models.DecimalField(verbose_name="Profondeur en cm", max_digits=5, decimal_places=2)  # Depth in cm
    bedsore_evolution = models.CharField(
        max_length=8,
        choices=BedsoreEvolutionStatus.choices,
        default=BedsoreEvolutionStatus.NA)
    # treatment can be null
    treatment = models.TextField(blank=True, null=True)  # Treatment description
    remarks = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to=update_bedsore_pictures_filenames, validators=[validate_image])

    class Meta:
        verbose_name = "Evaluation"
        verbose_name_plural = "Evaluations"
        ordering = ['-evaluation_date']


class BedsoreRiskAssessment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    assessment_date = models.DateField()

    # Critères du score de Braden
    sensory_perception = models.IntegerField(
        choices=[(1, 'Complètement limitée'), (2, 'Très limitée'), (3, 'Légèrement limitée'), (4, 'Pas de limitation')])
    moisture = models.IntegerField(
        choices=[(1, 'Constamment humide'), (2, 'Très humide'), (3, 'Occasionnellement humide'),
                 (4, 'Rarement humide')])
    activity = models.IntegerField(
        choices=[(1, 'Alité'), (2, 'Fauteuil'), (3, 'Marche occasionnellement'), (4, 'Marche fréquemment')])
    mobility = models.IntegerField(
        choices=[(1, 'Complètement immobile'), (2, 'Très limitée'), (3, 'Légèrement limitée'),
                 (4, 'Pas de limitation')])
    nutrition = models.IntegerField(
        choices=[(1, 'Très mauvaise'), (2, 'Probablement inadéquate'), (3, 'Adéquate'), (4, 'Excellente')])
    friction_shear = models.IntegerField(
        choices=[(1, 'Problème significatif'), (2, 'Problème potentiel'), (3, 'Pas de problème apparent')])

    def calculate_braden_score(self):
        return self.sensory_perception + self.moisture + self.activity + self.mobility + self.nutrition + self.friction_shear

    def __str__(self):
        braden_score = self.calculate_braden_score()
        risk_level = ""

        if braden_score <= 9:
            risk_level = "Très haut risque"
        elif 10 <= braden_score <= 12:
            risk_level = "Haut risque"
        elif 13 <= braden_score <= 14:
            risk_level = "Risque modéré"
        elif 15 <= braden_score <= 18:
            risk_level = "Risque faible"
        else:
            risk_level = "Risque très faible"

        return f"Évaluation du risque pour {self.patient.first_name} {self.patient.name} le {self.assessment_date}. Score de Braden : {braden_score} ({risk_level})"

    class Meta:
        verbose_name = "Évaluation du risque de développer une escarre"
        verbose_name_plural = "Évaluations du risque de développer une escarre"
        ordering = ['-assessment_date']


class AlternateAddress(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='addresses')
    full_address = models.TextField("Adresse complète", help_text="ex: 1 rue de la bonne santé, L-1214 Luxembourg",
                                    max_length=255)
    start_date = models.DateField()
    start_time = models.TimeField(blank=True, null=True)
    end_date = models.DateField(blank=True, null=True)
    end_time = models.TimeField(blank=True, null=True)

    def __str__(self):  # Python 3: def __str__(self):
        return 'from %s to %s %s is at %s' % (
            self.start_date, self.end_date, self.patient, self.full_address)

    # after save we need to update the address of the all the Events assigned to this patient in between the start and end date, take into consideration that end_date can be null
    def save(self, *args, **kwargs):
        super(AlternateAddress, self).save(*args, **kwargs)
        from invoices.events import Event
        if self.end_date is None:
            events = Event.objects.filter(patient=self.patient).filter(day__gte=self.start_date,
                                                                       time_start_event__gte=self.start_time if self.start_time else '00:00:00')
            events = events.filter(state__in=[1, 2])
            print("Found %d events : %s" % (events.count(), events))
        else:
            events = Event.objects.filter(patient=self.patient).filter(day__gte=self.start_date).filter(
                day__lte=self.end_date)
            # filter events that are in state (1, _('Waiting for validation')),
            #         (2, _('Valid')),
            events = events.filter(state__in=[1, 2])
            print("Found %d events : %s" % (events.count(), events))
        if len(events) > 5 and not os.environ.get('LOCAL_ENV', None):
            # call async task
            update_events_address.delay(events, self.full_address)
        else:
            for event in events:
                event.event_address = self.full_address
                event.clean()
                event.save()


class Hospitalization(models.Model):
    class Meta:
        ordering = ['-id']

    start_date = models.DateField(u"Début d'hospitlisation")
    end_date = models.DateField(u"Date de fin", default=None, blank=True, null=True)
    description = models.TextField(max_length=50, default=None, blank=True, null=True)
    patient = models.ForeignKey(Patient, related_name='hospitalizations',
                                help_text='Please enter hospitalization dates of the patient',
                                on_delete=models.CASCADE)

    def __str__(self):  # Python 3: def __str__(self):
        return 'From %s to %s for %s' % (self.start_date, self.end_date, self.patient)

    def as_dict(self):
        result = self.__dict__
        if self.patient and self.patient is not None:
            result['patient'] = self.patient

        return result

    def clean(self):
        exclude = []
        if self.patient is not None and self.patient.id is None:
            exclude = ['patient']

        super(Hospitalization, self).clean_fields(exclude)
        messages = self.validate(self.id, self.as_dict())
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(Hospitalization.validate_dates(data))
        result.update(Hospitalization.validate_prestation(data))
        result.update(Hospitalization.validate_patient_alive(data))

        return result

    @staticmethod
    def validate_dates(data):
        messages = {}
        is_valid = data['end_date'] is None or data['start_date'] <= data['end_date']
        if not is_valid:
            messages = {'end_date': 'End date must be bigger than Start date'}

        return messages

    @staticmethod
    def validate_prestation(data):
        messages = {}
        patient_id = None
        if 'patient' in data:
            patient_id = data['patient'].id
        elif 'patient_id' in data:
            patient_id = data['patient_id']
        else:
            messages = {'patient': 'Please fill Patient field'}

        start_date = datetime.combine(data['start_date'], datetime.min.time()).astimezone(ZoneInfo("Europe/Luxembourg"))
        if data['end_date']:
            end_date = datetime.combine(data['end_date'], datetime.max.time()).astimezone(ZoneInfo("Europe/Luxembourg"))
        else:
            end_date = None

        conflicts = Prestation.objects.filter(Q(date__range=(start_date, end_date))).filter(
            invoice_item__patient_id=patient_id).exclude(carecode__code__in=['FSP1', 'FSP2'])
        # build string of codes and dates of conflicts to display in error message CODE , DATE  - CODE , DATE (date should be in format dd/mm/yyyy)
        # Assuming your QuerySet is named 'qs'
        # InvoiceItem.objects.get(conflicts[0].id)
        display_codes_and_dates_of_conflicts = [
            f"Code: {item.carecode.code}, Date: {item.date.strftime('%d-%m-%Y %H:%M')} (invoice: {item.invoice_item.invoice_number})"
            for item in conflicts]
        if 0 < conflicts.count():
            messages = {
                'start_date': 'error 2807 Prestation(s) exist in selected dates range for this Patient %s' % display_codes_and_dates_of_conflicts}
        # conflicts for FSP1 and FSP2 are allowed if start date is 1 day after
        conflicts_fsp = Prestation.objects.filter(Q(date__range=(start_date + timedelta(days=1), end_date))).filter(
            invoice_item__patient_id=patient_id).filter(carecode__code__in=['FSP1', 'FSP2'])
        display_codes_and_dates_of_conflicts_fsp = [
            f"Code: {item.carecode.code}, Date: {item.date.strftime('%d-%m-%Y %H:%M')} (invoice: {item.invoice_item.invoice_number})"
            for item in conflicts_fsp]
        if 0 < conflicts_fsp.count():
            messages = {
                'start_date': 'error 2807953 Prestation(s) Palliative care exist in selected dates range for this Patient %s' % display_codes_and_dates_of_conflicts_fsp}

        return messages

    @staticmethod
    def validate_date_range(instance_id, data):
        messages = {}
        conflicts_cnt = Hospitalization.objects.filter(
            Q(start_date__range=(data['start_date'], data['end_date'])) |
            Q(end_date__range=(data['start_date'], data['end_date'])) |
            Q(start_date__lte=data['start_date'], end_date__gte=data['start_date']) |
            Q(start_date__lte=data['end_date'], end_date__gte=data['end_date'])
        ).filter(
            patient_id=data['patient'].id).exclude(
            pk=instance_id).count()
        if 0 < conflicts_cnt:
            messages = {'start_date': 'Intersection with other Hospitalizations'}

        return messages

    @staticmethod
    def validate_patient_alive(data):
        messages = {}
        patient = None
        if 'patient' in data:
            patient = data['patient']
        elif 'patient_id' in data:
            patient = Patient.objects.filter(pk=data['patient_id']).get()
        else:
            messages = {'patient': 'Please fill Patient field'}

        date_of_death = patient.date_of_death
        if date_of_death and data['end_date'] is None:
            messages = {'end_date': "Hospitalization end date must be set"}
            return messages
        if date_of_death and data['end_date'] > date_of_death:
            messages = {'end_date': "Hospitalization cannot be later than or include Patient's death date"}

        return messages


def update_medical_prescription_filename(instance, filename):
    file_name, file_extension = os.path.splitext(filename)
    if instance.date is None:
        _current_yr_or_prscr_yr = now().date().strftime('%Y')
        _current_month_or_prscr_month = now().date().strftime('%M')
    else:
        _current_yr_or_prscr_yr = str(instance.date.year)
        _current_month_or_prscr_month = str(instance.date.month)
    path = os.path.join("Medical Prescription", _current_yr_or_prscr_yr,
                        _current_month_or_prscr_month)
    filename_pre_str = f"{instance.prescriptor.name}_{instance.patient.name}_{instance.patient.first_name}_{str(instance.date)}"
    if (instance.file_upload.name.find(filename_pre_str) != -1):
        file_name_pdf, file_extension_pdf = os.path.splitext(instance.file_upload.name)
        filename = f"{file_name_pdf}{file_extension}"
        return filename

    # rewrite filename using f"{instance.prescriptor.name}_{instance.patient.name}_{instance.patient.first_name}_{str(instance.date)}_{uuid}{file_extension}"
    unique_id = uuid.uuid4().hex
    filename = f"{instance.prescriptor.name}_{instance.patient.name}_{instance.patient.first_name}_{str(instance.date)}_{unique_id}{file_extension}"
    filepath = os.path.join(path, filename)
    return filepath


def validate_image(image):
    try:
        file_size = image.file.size
    except:
        return
    limit_kb = 1024
    if file_size > limit_kb * 1024:
        raise ValidationError("Taille maximale du fichier est %s KO" % limit_kb)


class MedicalPrescription(models.Model):
    class Meta:
        ordering = ['-id']

    prescriptor = models.ForeignKey(Physician, related_name='medical_prescription',
                                    help_text='Please chose the Physician who is giving the medical prescription',
                                    on_delete=models.CASCADE)
    patient = models.ForeignKey(Patient, default=None, related_name='medical_prescription_patient',
                                help_text='Please chose the Patient who is receiving the medical prescription',
                                on_delete=models.CASCADE)
    date = models.DateField('Date ordonnance')
    end_date = models.DateField('Date fin des soins', null=True, blank=True)
    notes = models.TextField("Notes ou remarques",
                             help_text="Veuillez suivre la nomenclature suivante: Pathologies: ...; Antécédents: ...; Traitements: ...; Allergies: ...; Autres: ...",
                             max_length=1000,
                             blank=True, null=True)
    file_upload = models.FileField(null=True, blank=True, upload_to=update_medical_prescription_filename)
    # image_file = _modelscloudinary.CloudinaryField('Scan or picture', default=None,
    #                                                blank=True,
    #                                                null=True)
    thumbnail_img = models.ImageField("Aperçu", null=True, blank=True, upload_to=update_medical_prescription_filename)
    _original_file = None

    @property
    def file_description(self):
        return '%s %s %s' % (self.patient.name, self.patient.first_name, str(self.date))

    def __init__(self, *args, **kwargs):
        super(MedicalPrescription, self).__init__(*args, **kwargs)
        self._original_file = self.file_upload

    def get_admin_url(self):
        content_type = ContentType.objects.get_for_model(self.__class__)
        return reverse("admin:%s_%s_change" % (content_type.app_label, content_type.model), args=(self.id,))

    @property
    def image_preview(self, max_width=None, max_height=None):
        if max_width is None:
            max_width = '300'
        # used in the admin site model as a "thumbnail"
        # if value:
        #     r = requests.get(value.url, stream=True)
        #     encoded = ("data:" +
        #                r.headers['Content-Type'] + ";" +
        #                "base64," + base64.b64encode(r.content).decode('utf-8'))  # Convert to a string first
        #     context = {'imagedata': encoded, 'pdf_url': value.instance.file_upload.url}
        if not self.thumbnail_img:
            return '-'
        r = requests.get(self.thumbnail_img.url, stream=True)
        encoded = ("data:" +
                   r.headers['Content-Type'] + ";" +
                   "base64," + base64.b64encode(r.content).decode('utf-8'))
        styles = "max-width: %spx; max-height: %spx;" % (max_width, 300)
        tag = '<img src="{}" style="{}"/>'.format(encoded, styles)

        return mark_safe(tag)

    def clean(self):
        logger.info('clean medical prescription %s' % self)
        exclude = []
        if self.patient is not None and self.patient.id is None:
            exclude = ['patient']

        super(MedicalPrescription, self).clean_fields(exclude)
        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(MedicalPrescription.validate_dates(data))

        return result

    @staticmethod
    def validate_dates(data):
        messages = {}
        is_valid = data['end_date'] is None or data['date'] <= data['end_date']
        if not is_valid:
            messages = {'end_date': 'End date must be bigger than Start date'}

        return messages

    def get_original_file(self):
        return self._original_file

    @staticmethod
    def autocomplete_search_fields():
        return 'date', 'prescriptor__name', 'prescriptor__first_name', 'patient__name', 'patient__first_name', \
            'prescriptor__provider_code'

    def __str__(self):
        if self.notes is None:
            return 'Dr. %s %s (%s) pour %s' % (
                self.prescriptor.name.strip(), self.prescriptor.first_name.strip(), self.date,
                self.patient.name.strip())
        return 'Dr. %s %s (%s) pour %s [%s...]' % (
            self.prescriptor.name.strip(), self.prescriptor.first_name.strip(), self.date,
            self.patient.name.strip(),
            self.notes.replace('\n', '-').replace(' ', '-')[:10])


def update_patient_admin_filename(instance, filename):
    # if file_date is None:
    file_name, file_extension = os.path.splitext(filename)
    if instance.file_date is None:
        return 'patient_admin/%s/%s/%s/%s' % (str(instance.patient), timezone.now().year,
                                              timezone.now().month,
                                              filename)
    else:
        return 'patient_admin/%s/%s/%s/%s' % (str(instance.patient), instance.file_date.year, instance.file_date.month,
                                              filename)


class PatientAdminFile(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    file_description = models.CharField("description", max_length=50)
    file_date = models.DateField("date du fichier", null=True, blank=True)
    file_upload = models.FileField(null=True, blank=True, upload_to=update_patient_admin_filename)


@receiver(pre_save, sender=MedicalPrescription, dispatch_uid="medical_prescription_clean_gdrive_pre_save")
def medical_prescription_clean_gdrive_pre_save(sender, instance, **kwargs):
    if instance.thumbnail_img:
        old_file_name = instance.thumbnail_img.name
        old_file_name_path, old_file_name_ext = os.path.splitext(old_file_name)
        old_file_name_pdf = f"{old_file_name_path}.pdf"
        new_file_name_pdf = instance.file_upload.name
        if instance.file_upload._committed:
            new_file_name_pdf = update_medical_prescription_filename(instance, old_file_name_pdf)
        if (new_file_name_pdf != old_file_name_pdf):
            storage = default_storage
            if storage.exists(old_file_name_pdf):
                my_file = instance.file_upload.storage.open(old_file_name_pdf, 'rb')
                if instance.file_upload._committed:
                    instance.file_upload.storage.save(new_file_name_pdf, my_file)
                    my_file.close()
                    instance.file_upload.name = new_file_name_pdf
                instance.file_upload.storage.delete(old_file_name_pdf)
    if instance.file_upload:
        instance.thumbnail_img.delete(save=False)
        thumbnail_images = convert_from_bytes(instance.file_upload.read(), fmt='png', dpi=200, size=(300, None))
        instance.thumbnail_img = ImageFile(thumbnail_images[0].fp, name="thubnail.png")


# @receiver(pre_save, sender=MedicalPrescription, dispatch_uid="medical_prescription_clean_gdrive_post_save")
# def medical_prescription_clean_gdrive_post_save(sender, instance, **kwargs):
# if instance.file_upload:
#     pdf = requests.get(instance.file_upload.url, stream=True)
#     thumbnail_images = convert_from_bytes(pdf.raw.read(), dpi=200, size=(400, None))
#     instance.thumbnail_img = thumbnail_images[0]
#     instance.save()


@receiver(post_delete, sender=MedicalPrescription, dispatch_uid="medical_prescription_clean_gdrive_post_delete")
def medical_prescription_clean_gdrive_post_delete(sender, instance, **kwargs):
    if instance.file_upload.name:
        instance.file_upload.delete(save=False)
        instance.thumbnail_img.delete(save=False)


def get_default_invoice_number():
    default_invoice_number = 0
    max_invoice_number = InvoiceItem.objects.filter(Q(invoice_number__iregex=r'^\d+$')).annotate(
        invoice_number_int=Cast('invoice_number', IntegerField())).aggregate(Max('invoice_number_int'))

    if max_invoice_number['invoice_number_int__max'] is not None:
        default_invoice_number = max_invoice_number['invoice_number_int__max']

    default_invoice_number += 1

    return default_invoice_number


def invoiceitembatch_filename(instance, filename):
    return "Batch Path"


class InvoiceItemBatch(models.Model):
    start_date = models.DateField('Invoice batch start date')
    end_date = models.DateField('Invoice batch end date')
    send_date = models.DateField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    batch_description = models.CharField("description", max_length=50, null=True, blank=True)
    force_update = models.BooleanField(default=False)
    version = models.IntegerField(default=0)
    medical_prescriptions = models.FileField("Ordonnances", blank=True, null=True,
                                             upload_to=invoice_itembatch_ordo_filename)
    prefac_file = models.FileField("Fichier Plat facturation", blank=True, null=True,
                                   upload_to=invoice_itembatch_prefac_filename)
    generated_invoice_files = models.FileField("Facture CNS PDF", blank=True, null=True,
                                               upload_to=invoice_itembatch_medical_prescription_filename)
    batch_type = models.CharField(max_length=50, choices=BatchTypeChoices.choices, default=BatchTypeChoices.CNS_INF)

    # creation technical fields
    created_date = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    _original_file = None

    # invoices to be corrected
    # total_amount

    def __str__(self):  # Python 3: def __str__(self):
        return 'from %s to %s - %s' % (self.start_date, self.end_date, self.batch_description)

    def __init__(self, *args, **kwargs):
        super(InvoiceItemBatch, self).__init__(*args, **kwargs)
        self._original_file = self.generated_invoice_files

    @property
    def count_invoices(self):
        return self.get_invoices().count()

    def get_original_file(self):
        return self._original_file

    def clean(self):
        exclude = []
        super(InvoiceItemBatch, self).clean_fields(exclude)
        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(InvoiceItemBatch.validate_dates(data))
        result.update(InvoiceItemBatch.validate_force_update_and_send_date_are_set(data))
        return result

    def validate_force_update_and_send_date_are_set(data):
        messages = {}
        if data['force_update'] and data['send_date'] is None:
            messages = {'send_date': 'Send date is mandatory when force update is true'}
        if data['force_update'] and data['batch_description'] is None:
            messages = {'batch_description': 'Description is mandatory when force update is true'}
        return messages

    @staticmethod
    def validate_dates(data):
        messages = {}
        is_valid = data['end_date'] is None or data['start_date'] <= data['end_date']
        if not is_valid:
            messages = {'end_date': 'End date must be bigger than Start date'}

        return messages

    def get_invoices(self):
        return InvoiceItem.objects.filter(batch=self).order_by('patient_id', 'invoice_number')

    def events_during_batch_periods(self):
        from invoices.events import Event
        from invoices.enums.event import EventTypeEnum
        events = Event.objects.filter(day__range=(self.start_date, self.end_date)).exclude(patient__isnull=True).filter(
            patient__is_under_dependence_insurance=False).exclude(event_type_enum=EventTypeEnum.BIRTHDAY).order_by("patient__name", "day")
        # grouped_events = events.values('patient__name').annotate(event_count=Count('id'))
        dirty_events = []
        for evt in events:
            count_prestas = Prestation.objects.filter(date__date=evt.day, invoice_item__patient=evt.patient).count()
            if count_prestas == 0:
                dirty_events.append(evt)
        return dirty_events


# @receiver(pre_save, sender=InvoiceItemBatch, dispatch_uid="invoiceitembatch_pre_save")
# def invoiceitembatch_generate_pdf_name(sender, instance, **kwargs):
#     instance.file_upload = InvoiceItemBatchPdf.get_filename(instance)
#     origin_file = instance.get_original_file()
#     if origin_file.name and origin_file != instance.file_upload:
#         batch_gd_storage.delete(origin_file.name)


@receiver(post_save, sender=InvoiceItemBatch, dispatch_uid="invoiceitembatch_post_save")
def invoiceitembatch_generate_pdf(sender, instance, **kwargs):
    if os.environ.get('LOCAL_ENV', None):
        print("Direct call post_save on InvoiceItemBatch %s" % instance)
        process_post_save(instance)
    else:
        print("Call post_save on InvoiceItemBatch %s via redis /rq " % instance)
        process_post_save.delay(instance)


@receiver(post_delete, sender=InvoiceItemBatch, dispatch_uid="invoiceitembatch_post_delete")
def medical_prescription_clean_gdrive_post_delete(sender, instance, **kwargs):
    print("post_delete")
    # if instance.file_upload.name:
    #    gd_storage.delete(instance.file_upload.name)


class PaymentReference(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateField(blank=True, null=True, default=None)
    invoice_list = models.CharField(max_length=200)

    def __str__(self):
        return "%s" % self.invoice_list


class InvoiceItem(models.Model):
    class Meta(object):
        ordering = ['-id']
        verbose_name = u"Mémoire d'honoraire"
        verbose_name_plural = u"Mémoires d'honoraire"

    PRESTATION_LIMIT_MAX = 20
    invoice_details = models.ForeignKey(InvoicingDetails,
                                        related_name='invoicing_details_link',
                                        on_delete=models.PROTECT)
    invoice_number = models.CharField(max_length=50, unique=True, default=get_default_invoice_number)
    is_private = models.BooleanField('Facture pour patient non pris en charge par CNS',
                                     help_text=u'Seuls les patients qui ne disposent pas de la prise en charge CNS '
                                               u'seront recherchés dans le champ Patient (privé)',
                                     default=False)
    patient = models.ForeignKey(Patient, related_name='invoice_items',
                                help_text=u"choisir parmi les patients en entrant quelques lettres de son nom ou prénom",
                                on_delete=models.CASCADE)
    # subcontractor = models.ForeignKey(Patient, related_name='invoice_subcontractor',
    #                                   help_text=u'Si vous introduisez un sous traitant',
    #                                   on_delete=models.CASCADE, null=True, blank=True)
    accident_id = models.CharField(max_length=30, help_text=u"Numéro d'accident est facultatif", null=True, blank=True)
    accident_date = models.DateField(help_text=u"Date d'accident est facultatif", null=True, blank=True)
    invoice_date = models.DateField('Invoice date')
    patient_invoice_date = models.DateField('Date envoi au patient', null=True, blank=True)
    invoice_send_date = models.DateField('Date envoi facture', null=True, blank=True)
    invoice_sent = models.BooleanField(default=False)
    invoice_paid = models.BooleanField(default=False)
    batch = models.ForeignKey(InvoiceItemBatch, related_name='invoice_items', null=True, blank=True,
                              on_delete=models.SET_NULL)
    is_valid = models.BooleanField(default=True)
    validation_comment = models.TextField(null=True, blank=True)
    medical_prescription = models.ForeignKey(MedicalPrescription, related_name='invoice_items', null=True, blank=True,
                                             help_text='Please choose a Medical Prescription',
                                             on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=50, null=True, blank=True)
    xero_invoice_url = models.URLField(null=True, blank=True)

    def clean(self, *args, **kwargs):
        super(InvoiceItem, self).clean_fields()
        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @property
    def number_of_prestations(self):
        if self.prestations:
            return self.prestations.count()
        return "-"

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(InvoiceItem.validate_is_private(data))
        result.update(InvoiceItem.validate_patient(data))
        return result

    def add_prestation(self, prestation):
        if self.prestations.count() >= self.PRESTATION_LIMIT_MAX:
            raise ValidationError("Maximum number of prestations reached")
        self.prestations.add(prestation)

    def get_prestations(self):
        return self.prestations.all().order_by('date')

    def get_prestations_and_events_associated(self):
        # get prestations and group them by date
        prestations = self.prestations.all().order_by('date')
        from invoices.events import Event
        from invoices.data.invoice_checks import PrestationEvent
        prestation_evts = []
        for prestation in prestations:
            # get event of same date
            evt = Event.objects.filter(day=prestation.date.date(), patient=self.patient).all()
            evts = []
            for e in evt:
                evts.append(e)
            # PrestationEvent(care_date=prestation.date.date(), events=evts, prestation=prestation)
            prestation_evts.append(
                PrestationEvent(care_date=prestation.date.date(), events=evts, prestation=prestation))
        return prestation_evts

    @staticmethod
    def validate_is_private(data):
        messages = {}
        if data['is_private']:
            patient = None
            if 'patient' in data:
                patient = data['patient']
            elif 'patient_id' in data:
                patient = Patient.objects.filter(pk=data['patient_id']).get()
            else:
                messages = {'patient': 'Please fill Patient field'}

            if patient is not None and data['is_private'] != patient.is_private:
                messages = {'patient': 'Only private Patients allowed in private Invoice Item.'}

        return messages

    @staticmethod
    def validate_patient(data):
        messages = {}
        if 'medical_prescription_id' in data or 'medical_prescription' in data:
            medical_prescription = None
            if 'medical_prescription' in data:
                medical_prescription = data['medical_prescription']
            elif 'medical_prescription_id' in data:
                try:
                    medical_prescription = MedicalPrescription.objects.filter(pk=data['medical_prescription_id']).get()
                except MedicalPrescription.DoesNotExist:
                    medical_prescription = None

            patient = None
            if 'patient' in data:
                patient = data['patient']
            elif 'patient_id' in data:
                patient = Patient.objects.filter(pk=data['patient_id']).get()
            else:
                messages = {'patient': 'Please fill Patient field'}

            if medical_prescription is not None and patient != medical_prescription.patient:
                messages = {
                    'medical_prescription': "MedicalPrescription's Patient must be equal to InvoiceItem's Patient"}

        return messages

    @property
    def invoice_month(self):
        return self.invoice_date.strftime("%B %Y")

    def __str__(self):
        return 'invoice no.: %s - nom patient: %s' % (self.invoice_number, self.patient)

    @staticmethod
    def autocomplete_search_fields():
        return 'invoice_number',

    def get_first_medical_prescription(self):
        return InvoiceItemPrescriptionsList.objects.filter(
            invoice_item=self).first() if InvoiceItemPrescriptionsList.objects.filter(
            invoice_item=self).exists() else None

    def get_first_valid_medical_prescription(self, prestation_date):
        return InvoiceItemPrescriptionsList.objects.filter(
            invoice_item=self, medical_prescription__date__lte=prestation_date,
            medical_prescription__end_date__gte=prestation_date).first() if InvoiceItemPrescriptionsList.objects.filter(
            invoice_item=self, medical_prescription__date__lte=prestation_date,
            medical_prescription__end_date__gte=prestation_date).exists() else None

    def get_all_medical_prescriptions(self):
        return InvoiceItemPrescriptionsList.objects.filter(invoice_item=self)


class InvoiceItemPrescriptionsList(models.Model):
    # verbose name is Liste des ordonnances
    class Meta:
        verbose_name = 'Liste des ordonnances'
        verbose_name_plural = 'Liste des ordonnances'

    invoice_item = models.ForeignKey(InvoiceItem, on_delete=models.CASCADE, related_name='prescriptions')
    medical_prescription = models.ForeignKey(MedicalPrescription, verbose_name="Ordonnance",
                                             on_delete=models.CASCADE,
                                             related_name='med_prescription_multi_invoice_items', blank=True,
                                             null=True)

    def __str__(self):
        return self.invoice_item.invoice_number + ' - ' + str(self.medical_prescription.patient) + ' - ' + \
            str(self.medical_prescription)


class InvoiceItemEmailLog(models.Model):
    item = models.ForeignKey(InvoiceItem, on_delete=models.CASCADE, related_name='emails')
    sent_at = models.DateTimeField(auto_now_add=True)
    recipient = models.EmailField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    cc = models.CharField(max_length=200, blank=True)
    bcc = models.CharField(max_length=200, blank=True)
    attachments = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=200, blank=True)
    error = models.TextField(blank=True)

    def __str__(self):
        # return recipient, subject, datetime
        return self.recipient + ' - ' + self.subject + ' - ' + self.sent_at.strftime("%d/%m/%Y %H:%M:%S")


class Prestation(models.Model):
    class Meta:
        ordering = ['-date']

    invoice_item = models.ForeignKey(InvoiceItem,
                                     related_name='prestations',
                                     on_delete=models.CASCADE)
    employee = models.ForeignKey('invoices.Employee',
                                 related_name='prestations',
                                 blank=True,
                                 null=True,
                                 default=settings.AUTH_USER_MODEL,
                                 on_delete=models.CASCADE)
    carecode = models.ForeignKey(CareCode,
                                 related_name='prestations',
                                 on_delete=models.CASCADE)
    quantity = IntegerField(default=1)
    date = models.DateTimeField('date')
    at_home = models.BooleanField(default=False)
    at_home_paired = models.OneToOneField('self',
                                          related_name='paired_at_home',
                                          blank=True,
                                          null=True,
                                          default=None,
                                          on_delete=models.CASCADE)
    date.editable = True

    @property
    def paired_at_home_name(self):
        return str(self.paired_at_home)

    @property
    def at_home_paired_name(self):
        return str(self.at_home_paired)

    def as_dict(self):
        result = self.__dict__
        if self.invoice_item and self.invoice_item.patient is not None:
            result['patient'] = self.invoice_item.patient
            result['invoice_item'] = self.invoice_item

        return result

    def clean(self):
        exclude = []
        if self.invoice_item is not None and self.invoice_item.id is None:
            exclude = ['invoice_item']

        super(Prestation, self).clean_fields(exclude)
        messages = self.validate(self.id, self.as_dict())
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(Prestation.validate_patient_hospitalization(data))
        result.update(Prestation.validate_at_home_default_config(data))
        result.update(Prestation.validate_carecode(instance_id, data))
        result.update(Prestation.validate_patient_alive(data))
        result.update(Prestation.validate_max_limit(data))
        result.update(Prestation.validate_employee(data))
        return result

    @staticmethod
    def validate_employee(data):
        messages = {}
        employee = None
        if 'employee' in data:
            employee = data['employee']
        elif 'employee_id' in data and data['employee_id'] is not None:
            employee = Employee.objects.filter(pk=data['employee_id']).get()
        else:
            messages = {'employee': 'Please fill Employee field'}
        return messages

    @staticmethod
    def validate_at_home_default_config(data):
        messages = {}
        at_home = 'at_home' in data and data['at_home']
        if at_home and not CareCode.objects.filter(code=config.AT_HOME_CARE_CODE).exists():
            msg = "CareCode %s does not exist. Please create a CareCode with the Code %s" % (
                config.AT_HOME_CARE_CODE, config.AT_HOME_CARE_CODE)
            messages = {'at_home': msg}

        return messages

    @staticmethod
    def validate_patient_hospitalization(data):
        messages = {}
        invoice_item_id = None
        care_code_code = None
        if 'patient' in data:
            patient = data['patient']
        else:
            if 'invoice_item' in data:
                invoice_item_id = data['invoice_item'].id
                invoice_item = data['invoice_item']
            elif 'invoice_item_id' in data:
                invoice_item_id = data['invoice_item_id']
            else:
                messages = {'invoice_item_id': 'Please fill InvoiceItem field'}
            patient = Patient.objects.filter(invoice_items__in=[invoice_item_id]).get()

        if 'carecode_id' in data:
            care_code_code = CareCode.objects.filter(pk=data['carecode_id']).get().code

        if care_code_code in ["FSP1", "FSP2"]:
            hospitalizations_cnt = Hospitalization.objects.filter(patient=patient,
                                                                  start_date__lt=data['date'],
                                                                  end_date__gte=data['date']).count()
        else:
            hospitalizations_cnt = Hospitalization.objects.filter(patient=patient,
                                                                  start_date__lte=data['date'],
                                                                  end_date__gte=data['date']).count()
        if 0 < hospitalizations_cnt:
            messages = {'date': 'Patient has hospitalization records for the chosen date'}

        return messages

    @staticmethod
    def validate_carecode(instance_id, data):
        messages = {}
        carecode = None
        if 'carecode' in data:
            carecode = data['carecode']
        elif 'carecode_id' in data:
            carecode = CareCode.objects.filter(pk=data['carecode_id']).get()
        else:
            messages = {'carecode_id': 'Please fill CareCode field'}

        invoice_item_id = None
        if 'invoice_item' in data:
            invoice_item_id = data['invoice_item'].id
        elif 'invoice_item_id' in data:
            invoice_item_id = data['invoice_item_id']
        else:
            messages = {'invoice_item_id': 'Please fill InvoiceItem field'}

        exclusive_care_codes = carecode.exclusive_care_codes.all()
        prestations_queryset = Prestation.objects.filter(
            (Q(carecode__in=exclusive_care_codes) | Q(carecode=carecode.id)) & Q(date=data['date']) & Q(
                invoice_item_id=invoice_item_id)).exclude(pk=instance_id)
        prestations_list = prestations_queryset[::1]

        if 0 != len(prestations_list):
            conflicting_codes = ", ".join([prestation.carecode.code for prestation in prestations_list])
            msg = "CareCode %s cannot be applied because CareCode(s) %s has been applied already" % (
                carecode.code, conflicting_codes)

            messages = {'carecode': msg}

        return messages

    @staticmethod
    def validate_patient_alive(data):
        messages = {}
        invoice_item = None
        if 'patient' in data:
            patient = data['patient']
        else:
            if 'invoice_item' in data:
                invoice_item = data['invoice_item']
            elif 'invoice_item_id' in data:
                invoice_item = InvoiceItem.objects.filter(pk=data['invoice_item_id']).get()
            else:
                messages = {'invoice_item_id': 'Please fill InvoiceItem field'}

            patient = invoice_item.patient

        date_of_death = patient.date_of_death
        if date_of_death is not None and data['date'].date() >= date_of_death:
            messages = {'date': "Prestation date cannot be later than or equal to Patient's death date"}

        return messages

    @staticmethod
    def validate_max_limit(data):
        messages = {}
        invoice_item = None
        if 'invoice_item' in data:
            invoice_item = data['invoice_item']
        elif 'invoice_item_id' in data:
            invoice_item = InvoiceItem.objects.filter(pk=data['invoice_item_id']).get()
        else:
            messages = {'invoice_item_id': 'Please fill InvoiceItem field'}

        max_limit = InvoiceItem.PRESTATION_LIMIT_MAX
        if invoice_item.id is None:
            return messages
        existing_prestations = invoice_item.prestations
        existing_count = existing_prestations.count()
        expected_count = existing_count
        adds_new = False
        if 'at_home' in data and data['at_home']:
            at_home_prestation_exists = existing_prestations.filter(carecode__code=config.AT_HOME_CARE_CODE).exists()
            if not at_home_prestation_exists:
                expected_count += 1
                adds_new = True
        if 'id' not in data or data['id'] is None:
            expected_count += 1
            adds_new = True

        if adds_new and expected_count > max_limit:
            messages = {
                'date': "Max number of Prestations for one InvoiceItem is %s" % (str(InvoiceItem.PRESTATION_LIMIT_MAX))}

        return messages

    def __str__(self):  # Python 3: def __str__(self):
        return '%s - %s' % (self.carecode.code, self.carecode.name)

    @staticmethod
    def autocomplete_search_fields():
        return 'patient__name', 'patient__first_name'


@receiver(post_save, sender=Prestation, dispatch_uid="create_at_home_prestation")
def create_prestation_at_home_pair(sender, instance, **kwargs):
    if instance.at_home and instance.at_home_paired is None and not hasattr(instance, 'paired_at_home'):
        at_home_carecode = CareCode.objects.get(code=config.AT_HOME_CARE_CODE)
        at_home_pair_exists = Prestation.objects.filter(invoice_item=instance.invoice_item, date=instance.date,
                                                        carecode=at_home_carecode).exists()
        if not at_home_pair_exists:
            pair = deepcopy(instance)
            pair.pk = None
            pair.carecode = at_home_carecode
            pair.at_home = False
            pair.at_home_paired = instance
            pair.save()


@receiver(post_save, sender=Patient, dispatch_uid="create_contact_in_employees_google_contacts")
def create_contact_in_employees_google_contacts(sender, instance, **kwargs):
    all_active_employees = Employee.objects.filter(end_contract__isnull=True)
    # is it a new patient or an update
    for employee in all_active_employees:
        google_contact = GoogleContacts(email=employee.user.email)
        if settings.TESTING:
            print("** TEST mode")
        else:
            if os.environ.get('LOCAL_ENV', None):
                print("** LOCAL_ENV mode - no call")
                # google_contact.create_or_update_new_patient(instance)
            else:
                async_create_or_update_new_patient.delay(google_contacts_instance=google_contact, patient=instance)


@receiver(post_delete, sender=Patient, dispatch_uid="delete_contact_in_employees_google_contacts")
def delete_contact_in_employees_google_contacts(sender, instance, **kwargs):
    all_active_employees = Employee.objects.filter(end_contract__isnull=True)
    for employee in all_active_employees:
        google_contact = GoogleContacts(email=employee.user.email)
        # if local env call directly
        if os.environ.get('LOCAL_ENV', None):
            google_contact.delete_patient(instance)
        else:
            async_delete_patient.delay(google_contacts_instance=google_contact, patient=instance)


from constance import config
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from invoices.enums.alertlevels import AlertLevels


class Alert(models.Model):
    text_alert = models.CharField(_("Text alert"), max_length=255)
    # alert level 1 = info, 2 = warning, 3 = danger link to alert_level enum
    alert_level = models.CharField(_("Alert level"), max_length=20, choices=AlertLevels.choices)
    date_alert = models.DateTimeField(_("Date Alert"), auto_now_add=True)
    is_read = models.BooleanField(_("Is Read"), default=False)
    date_read = models.DateTimeField(_("Date Read"), null=True, blank=True)
    is_active = models.BooleanField(_("Is active"), default=True)
    link_to_object = models.URLField(max_length=255, null=True, blank=True)
    link_to_object_name = models.CharField(max_length=255, null=True, blank=True)
    link_to_object_id = models.IntegerField(null=True, blank=True)
    comment = models.TextField(_("Comment"), null=True, blank=True, max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    alert_created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                                         related_name="alert_created_by")

    def __str__(self):
        return "{0} - {1}".format(self.alert_level, self.text_alert)

    # when alert is saved check if it is a new alert and send email to user
    def get_admin_url(self):
        model_name = self._meta.model_name
        app_label = self._meta.app_label
        return reverse('admin:{0}_{1}_change'.format(app_label, model_name), args=[self.id])

    class Meta:
        verbose_name = _("Alert")
        verbose_name_plural = _("Alerts")
        ordering = ['-date_alert']


# @receiver(post_save, sender=Alert, dispatch_uid="post_save_alert_receiver")
# def post_save_alert_receiver(sender, instance, created, *args, **kwargs):
#     if created:
#         if instance.pk is not None and not instance.is_read and instance.is_active:
#             url = "%s%s " % (config.ROOT_URL, instance.get_admin_url())
#             notify_user_that_new_alert_is_created(instance, url, instance.user.email)
#         # if is_read is true set date_read to now
#         if instance.is_read:
#             instance.date_read = datetime.now()
