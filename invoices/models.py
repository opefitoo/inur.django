# -*- coding: utf-8 -*-
import logging
import os
import uuid
import re
from copy import deepcopy

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
    date_of_death = models.DateField(u"Date de décès",default=None, blank=True, null=True)

    @staticmethod
    def autocomplete_search_fields():
        return 'name', 'first_name'

    def __unicode__(self):  # Python 3: def __str__(self):,
        return '%s %s' % (self.name.strip(), self.first_name.strip())

    def clean(self, *args, **kwargs):
        super(Patient, self).clean()
        is_code_sn_valid, message = self.is_code_sn_valid(self.is_private, self.code_sn)
        if not is_code_sn_valid:
            raise ValidationError({'code_sn': message})

    @staticmethod
    def is_code_sn_valid(is_private, code_sn):
        is_valid = True
        message = ''
        if not is_private:
            pattern = re.compile('^([1-9]{1}[0-9]{12})$')
            if pattern.match(code_sn) is None:
                message = 'Code SN should start with non zero digit and be followed by 12 digits'
                is_valid = False
            elif Patient.objects.filter(code_sn=code_sn).count() > 0:
                message = 'Code SN must be unique'
                is_valid = False

        return is_valid, message

class Hospitalization(models.Model):
    start_date = models.DateField(u"Début d'hospitlisation")
    end_date = models.DateField(u"Date de fin")
    description = models.TextField(max_length=50,default=None, blank=True, null=True,)
    hospitalizations_periods = models.ForeignKey(Patient, related_name='patient_hospitalization',
                                    help_text='Please enter hospitalization dates of the patient')


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
    path = 'medical-prescription'

    return os.path.join(path, filename)


class MedicalPrescription(models.Model):
    prescriptor = models.ForeignKey(Physician, related_name='medical_prescription',
                                    help_text='Please chose the Physician who is giving the medical prescription')
    date = models.DateField('Date ordonnance', null=True, blank=True)
    file = models.ImageField(storage=gd_storage, blank=True, upload_to=update_medical_prescription_filename)
    _original_file = None

    def __init__(self, *args, **kwargs):
        super(MedicalPrescription, self).__init__(*args, **kwargs)
        self._original_file = self.file

    def image_preview(self):
        # used in the admin site model as a "thumbnail"
        link = self.file.storage.get_thumbnail_link(self.file.name)
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
    # TODO: when checked only patient which is_private = true must be looked up via the ajax search lookup
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
        if self.patient_id is not None and self.is_private != self.patient.is_private:
            raise ValidationError({'patient': 'Only private Patients allowed in private Invoice Item.'})

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
        if self.at_home and not self.check_default_at_home_carecode_exists():
            raise ValidationError(self.at_home_carecode_does_not_exist_msg())

        prestations_list = self.get_conflicting_prestations(self.id, self.carecode, self.invoice_item, self.date)
        is_valid = self.is_carecode_valid(prestations_list=prestations_list)
        if not is_valid:
            conflicting_codes = ", ".join([prestation.carecode.code for prestation in prestations_list])
            msg = "CareCode %s cannot be applied because CareCode(s) %s has been applied already" % (
                self.carecode.code, conflicting_codes)

            raise ValidationError({'carecode': msg})

    @staticmethod
    def check_default_at_home_carecode_exists():
        return CareCode.objects.filter(code=config.AT_HOME_CARE_CODE).exists()

    @staticmethod
    def at_home_carecode_does_not_exist_msg():
        return "CareCode %s does not exist. Please create a CareCode with the Code %s" % (
            config.AT_HOME_CARE_CODE, config.AT_HOME_CARE_CODE)

    @staticmethod
    def get_conflicting_prestations(prestation_id, carecode, invoice_item, date):
        exclusive_care_codes = carecode.exclusive_care_codes.all()
        prestations_queryset = Prestation.objects.filter(
            (Q(carecode__in=exclusive_care_codes) | Q(carecode=carecode.id)) & Q(date=date) & Q(
                invoice_item=invoice_item)).exclude(pk=prestation_id)
        prestations_list = prestations_queryset[::1]

        return prestations_list

    @staticmethod
    def is_carecode_valid(prestation_id=None, carecode=None, invoice_item=None, date=None, prestations_list=None):
        if prestations_list is None:
            prestations_list = Prestation.get_conflicting_prestations(prestation_id, carecode, invoice_item, date)

        is_valid = 0 == len(prestations_list)

        return is_valid

    # TODO retrieve is_private from Patient or compute it in a different way
    @property
    def net_amount(self):
        if not self.patient.is_private:
            if self.carecode.reimbursed:
                return round(((self.carecode.gross_amount * 88) / 100), 2) + self.fin_part
            else:
                return 0
        else:
            return 0

    # TODO retrieve partificaption statutaire from Patient or compute it in a different way
    @property
    def fin_part(self):
        "Returns the financial participation of the client"
        if self.patient.participation_statutaire:
            return 0
        # round to only two decimals
        # if self.date > normalized_price_switch_date:
        #    return round(((self.carecode.gross_amount * 12) / 100), 2)
        return round(((self.carecode.gross_amount * 12) / 100), 2)

    def __unicode__(self):  # Python 3: def __str__(self):
        return '%s - %s' % (self.carecode.code, self.carecode.name)

    @staticmethod
    def autocomplete_search_fields():
        return 'patient__name', 'patient__first_name'


@receiver(post_save, sender=Prestation, dispatch_uid="create_at_home_prestation")
def create_prestation_at_home_pair(sender, instance, **kwargs):
    if instance.at_home and instance.at_home_paired is None and not hasattr(instance, 'paired_at_home'):
        pair = deepcopy(instance)
        pair.pk = None
        pair.carecode = CareCode.objects.get(code=config.AT_HOME_CARE_CODE)
        pair.at_home = False
        pair.at_home_paired = instance
        pair.save()
