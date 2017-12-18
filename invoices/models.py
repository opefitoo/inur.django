# -*- coding: utf-8 -*-
import logging
import pytz
import os
import uuid
import re
from copy import deepcopy
from datetime import datetime

from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models import Q, IntegerField, Max
from django.db.models.functions import Cast
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils.safestring import mark_safe
from django_countries.fields import CountryField
from invoices import settings
from constance import config
from storages import CustomizedGoogleDriveStorage

# Define Google Drive Storage
gd_storage = CustomizedGoogleDriveStorage()

logger = logging.getLogger(__name__)
fs = FileSystemStorage(location=settings.MEDIA_ROOT)


class CareCode(models.Model):
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=100)
    reimbursed = models.BooleanField("Prise en charge par CNS", default=True)
    exclusive_care_codes = models.ManyToManyField("self", blank=True)

    def __unicode__(self):  # Python 3: def __str__(self):
        return '%s: %s' % (self.code, self.name)

    @staticmethod
    def autocomplete_search_fields():
        return 'name', 'code'


# TODO 2: CareCode cannot have start and end validity dates that overlap
# TODO 3: depending on Prestation date, gross_amount that is calculated in Invoice will differ
class ValidityDate(models.Model):
    start_date = models.DateField("date debut validite")
    end_date = models.DateField("date fin validite", blank=True, null=True)
    gross_amount = models.DecimalField("montant brut", max_digits=5, decimal_places=2)
    care_code = models.ForeignKey(CareCode, related_name='validity_dates')

    def __unicode__(self):  # Python 3: def __str__(self):
        return 'from %s to %s' % (self.start_date, self.end_date)

    def clean(self, *args, **kwargs):
        super(ValidityDate, self).clean()
        is_valid = self.check_dates(self.start_date, self.end_date)

        if not is_valid:
            raise ValidationError({'end_date': 'End date must be bigger than Start date'})

    @staticmethod
    def check_dates(start_date, end_date):
        is_valid = end_date is None or start_date <= end_date

        return is_valid


# TODO: synchronize patient details with Google contacts
class Patient(models.Model):
    code_sn = models.CharField(max_length=30)
    first_name = models.CharField(max_length=30)
    name = models.CharField(max_length=30)
    address = models.TextField(max_length=30)
    zipcode = models.CharField(max_length=10)
    city = models.CharField(max_length=30)
    country = CountryField(blank_label='...', blank=True, null=True)
    phone_number = models.CharField(max_length=30)
    email_address = models.EmailField(default=None, blank=True, null=True)
    participation_statutaire = models.BooleanField(default=False)
    is_private = models.BooleanField(default=False)
    date_of_death = models.DateField(u"Date de décès", default=None, blank=True, null=True)

    @staticmethod
    def autocomplete_search_fields():
        return 'name', 'first_name'

    def __unicode__(self):  # Python 3: def __str__(self):,
        return '%s %s' % (self.name.strip(), self.first_name.strip())

    def clean(self, *args, **kwargs):
        super(Patient, self).clean()
        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(Patient.validate_code_sn(instance_id, data))
        result.update(Patient.validate_date_of_death(instance_id, data))

        return result

    @staticmethod
    def validate_date_of_death(instance_id, data):
        messages = {}
        if 'date_of_death' in data and data['date_of_death'] is not None:
            if Prestation.objects.filter(date__gte=data['date_of_death'], invoice_item__patient_id=instance_id).count():
                messages = {'date_of_death': 'Prestation for a later date exists'}

            if Hospitalization.objects.filter(end_date__gte=data['date_of_death']).count():
                messages = {'date_of_death': 'Hospitalization that ends later exists'}

        return messages

    @staticmethod
    def validate_code_sn(instance_id, data):
        messages = {}
        if 'is_private' in data and not data['is_private']:
            pattern = re.compile('^([1-9]{1}[0-9]{12})$')
            if pattern.match(data['code_sn']) is None:
                messages = {'code_sn': 'Code SN should start with non zero digit and be followed by 12 digits'}
            elif Patient.objects.filter(code_sn=data['code_sn']).exclude(pk=instance_id).count() > 0:
                messages = {'code_sn': 'Code SN must be unique'}

        return messages


class Hospitalization(models.Model):
    start_date = models.DateField(u"Début d'hospitlisation")
    end_date = models.DateField(u"Date de fin")
    description = models.TextField(max_length=50, default=None, blank=True, null=True)
    patient = models.ForeignKey(Patient, related_name='hospitalizations',
                                help_text='Please enter hospitalization dates of the patient')

    def __unicode__(self):  # Python 3: def __str__(self):
        return 'From %s to %s for %s' % (self.start_date, self.end_date, self.patient)

    def clean(self):
        super(Hospitalization, self).clean()
        messages = self.validate(self.id, self.__dict__)
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

        start_date = datetime.combine(data['start_date'], datetime.min.time()).replace(tzinfo=pytz.utc)
        end_date = datetime.combine(data['end_date'], datetime.max.time()).replace(tzinfo=pytz.utc)
        conflicts_cnt = Prestation.objects.filter(Q(date__range=(start_date, end_date))).filter(
            invoice_item__patient_id=patient_id).count()
        if 0 < conflicts_cnt:
            messages = {'start_date': 'Prestation(s) exist in selected dates range for this Patient'}

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
        if date_of_death is not None and data['end_date'] >= date_of_death:
            messages = {'end_date': "Hospitalization cannot be later than or include Patient's death date"}

        return messages


# TODO: 1. can maybe be extending common class with Patient ?
# TODO: 2. synchronize physician details with Google contacts
class Physician(models.Model):
    provider_code = models.CharField(max_length=30)
    first_name = models.CharField(max_length=30)
    name = models.CharField(max_length=30)
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

    def __unicode__(self):  # Python 3: def __str__(self):
        return '%s %s' % (self.name.strip(), self.first_name.strip())


def update_medical_prescription_filename(instance, filename):
    path = os.path.join(CustomizedGoogleDriveStorage.MEDICAL_PRESCRIPTION_FOLDER, str(instance.date.year))

    return os.path.join(path, filename)


class MedicalPrescription(models.Model):
    prescriptor = models.ForeignKey(Physician, related_name='medical_prescription',
                                    help_text='Please chose the Physician who is giving the medical prescription')
    patient = models.ForeignKey(Patient, default=None, related_name='medical_prescription_patient',
                                help_text='Please chose the Patient who is receiving the medical prescription')
    date = models.DateField('Date ordonnance', null=True, blank=True)
    end_date = models.DateField('Date fin des soins', null=True, blank=True)
    file = models.ImageField(storage=gd_storage, blank=True, upload_to=update_medical_prescription_filename)
    _original_file = None

    def __init__(self, *args, **kwargs):
        super(MedicalPrescription, self).__init__(*args, **kwargs)
        self._original_file = self.file
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

    def image_preview(self):
        # used in the admin site model as a "thumbnail"
        link = self.file.storage.get_thumbnail_link(getattr(self.file, 'name', None))
        styles = "max-width: 800px; max-height: 800px;"
        tag = '<img src="{}" style="{}"/>'.format(link, styles)

        return mark_safe(tag)

    def get_original_file(self):
        return self._original_file

    @staticmethod
    def autocomplete_search_fields():
        return 'date', 'prescriptor__name', 'prescriptor__first_name'

    def __unicode__(self):  # Python 3: def __str__(self):
        return '%s %s' % (self.prescriptor.name.strip(), self.prescriptor.first_name.strip())


@receiver(pre_save, sender=MedicalPrescription, dispatch_uid="medical_prescription_clean_gdrive_pre_save")
def medical_prescription_clean_gdrive_pre_save(sender, instance, **kwargs):
    origin_file = instance.get_original_file()
    if origin_file.name and origin_file != instance.file:
        gd_storage.delete(origin_file.name)


@receiver(post_delete, sender=MedicalPrescription, dispatch_uid="medical_prescription_clean_gdrive_post_delete")
def medical_prescription_clean_gdrive_post_delete(sender, instance, **kwargs):
    if instance.file.name:
        gd_storage.delete(instance.file.name)


def get_default_invoice_number():
    default_invoice_number = 0
    max_invoice_number = InvoiceItem.objects.filter(Q(invoice_number__iregex=r'^\d+$')).annotate(
        invoice_number_int=Cast('invoice_number', IntegerField())).aggregate(Max('invoice_number_int'))

    if max_invoice_number['invoice_number_int__max'] is not None:
        default_invoice_number = max_invoice_number['invoice_number_int__max']

    default_invoice_number += 1

    return default_invoice_number


class InvoiceItem(models.Model):
    invoice_number = models.CharField(max_length=50, unique=True, default=get_default_invoice_number)
    is_private = models.BooleanField('Facture pour patient non pris en charge par CNS',
                                     help_text='Seuls les patients qui ne disposent pas de la prise en charge CNS seront recherches dans le champ Patient (prive)',
                                     default=False)
    patient = models.ForeignKey(Patient, related_name='invoice_items',
                                help_text=u"choisir parmi les patients en entrant quelques lettres de son nom ou prenom")
    accident_id = models.CharField(max_length=30, help_text=u"Numero d'accident est facultatif", null=True, blank=True)
    accident_date = models.DateField(help_text=u"Date d'accident est facultatif", null=True, blank=True)
    invoice_date = models.DateField('Invoice date')
    patient_invoice_date = models.DateField('Date envoi au patient', null=True, blank=True)
    invoice_send_date = models.DateField('Date envoi facture', null=True, blank=True)
    invoice_sent = models.BooleanField(default=False)
    invoice_paid = models.BooleanField(default=False)

    medical_prescription = models.ForeignKey(MedicalPrescription, related_name='invoice_items', null=True, blank=True,
                                             help_text='Please chose a Medical Prescription')

    def clean(self, *args, **kwargs):
        super(InvoiceItem, self).clean()
        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(InvoiceItem.validate_is_private(data))
        result.update(InvoiceItem.validate_patient(data))

        return result

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
                medical_prescription = data['patient']
            elif 'medical_prescription_id' in data:
                medical_prescription = MedicalPrescription.objects.filter(pk=data['medical_prescription_id']).get()

            patient = None
            if 'patient' in data:
                patient = data['patient']
            elif 'patient_id' in data:
                patient = Patient.objects.filter(pk=data['patient_id']).get()
            else:
                messages = {'patient': 'Please fill Patient field'}

            if patient != medical_prescription.patient:
                messages = {
                    'medical_prescription': "MedicalPrescription's Patient must be equal to InvoiceItem's Patient"}

        return messages

    @property
    def invoice_month(self):
        return self.invoice_date.strftime("%B %Y")

    def __unicode__(self):  # Python 3: def __str__(self):
        return 'invocie no.: %s - nom patient: %s' % (self.invoice_number, self.patient)

    @staticmethod
    def autocomplete_search_fields():
        return 'invoice_number',


class Prestation(models.Model):
    invoice_item = models.ForeignKey(InvoiceItem, related_name='prestations')
    employee = models.ForeignKey('invoices.Employee', related_name='prestations', blank=True, null=True, default=None)
    carecode = models.ForeignKey(CareCode, related_name='prestations')
    quantity = IntegerField(default=1)
    date = models.DateTimeField('date')
    at_home = models.BooleanField(default=False)
    at_home_paired = models.OneToOneField('self', related_name='paired_at_home', null=True)
    date.editable = True

    @property
    def paired_at_home_name(self):
        return str(self.paired_at_home)

    @property
    def at_home_paired_name(self):
        return str(self.at_home_paired)

    def clean(self):
        super(Prestation, self).clean()
        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(Prestation.validate_patient_hospitalization(data))
        result.update(Prestation.validate_at_home_default_config(data))
        result.update(Prestation.validate_carecode(instance_id, data))
        result.update(Prestation.validate_patient_alive(data))

        return result

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
        if 'invoice_item' in data:
            invoice_item_id = data['invoice_item'].id
        elif 'invoice_item_id' in data:
            invoice_item_id = data['invoice_item_id']
        else:
            messages = {'invoice_item_id': 'Please fill InvoiceItem field'}

        patient = Patient.objects.filter(invoice_items__in=[invoice_item_id]).get()
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
        if 'invoice_item' in data:
            invoice_item = data['invoice_item']
        elif 'invoice_item_id' in data:
            invoice_item = InvoiceItem.objects.filter(pk=data['invoice_item_id']).get()
        else:
            messages = {'invoice_item_id': 'Please fill InvoiceItem field'}

        date_of_death = invoice_item.patient.date_of_death
        if date_of_death is not None and data['date'].date() >= date_of_death:
            messages = {'date': "Prestation date cannot be later than or equal to Patient's death date"}

        return messages

    def __unicode__(self):  # Python 3: def __str__(self):
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
