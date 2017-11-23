import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, IntegerField, Max
from django.db.models.functions import Cast

logger = logging.getLogger(__name__)


class CareCode(models.Model):
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=100)
    gross_amount = models.DecimalField("montant brut", max_digits=5, decimal_places=2)
    reimbursed = models.BooleanField("Prise en charge par CNS", default=True)

    def __unicode__(self):  # Python 3: def __str__(self):
        return '%s: %s' % (self.code, self.name)


# TODO: synchronize patient details with Google contacts
class Patient(models.Model):
    code_sn = models.CharField(max_length=30)
    first_name = models.CharField(max_length=30)
    name = models.CharField(max_length=30)
    address = models.TextField(max_length=30)
    zipcode = models.CharField(max_length=10)
    city = models.CharField(max_length=30)
    country = models.CharField(max_length=30, blank=True, null=True)
    phone_number = models.CharField(max_length=30)
    email_address = models.EmailField(default=None, blank=True, null=True)
    participation_statutaire = models.BooleanField()
    is_private = models.BooleanField(default=False)

    def __unicode__(self):  # Python 3: def __str__(self):
        return '%s %s' % (self.name.strip(), self.first_name.strip())


# TODO: 1. can maybe be extending common class with Patient ?
# TODO: 2. synchronize physician details with Google contacts
class Physician(models.Model):
    provider_code = models.CharField(max_length=30)
    first_name = models.CharField(max_length=30)
    name = models.CharField(max_length=30)
    address = models.TextField(max_length=30)
    zipcode = models.CharField(max_length=10)
    city = models.CharField(max_length=30)
    country = models.CharField(max_length=30, blank=True, null=True)
    phone_number = models.CharField(max_length=30)
    fax_number = models.CharField(max_length=30, blank=True, null=True)
    email_address = models.EmailField(default=None, blank=True, null=True)

    def __unicode__(self):  # Python 3: def __str__(self):
        return '%s %s' % (self.name.strip(), self.first_name.strip())


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
    invoice_sent = models.BooleanField()
    invoice_paid = models.BooleanField()
    medical_prescription_date = models.DateField('Date ordonnance', null=True, blank=True)

    # TODO: I would like to store the file Field in Google drive
    # maybe this can be helpful https://github.com/torre76/django-googledrive-storage
    # upload_scan_medical_prescription = models.FileField()

    physician = models.ForeignKey(Physician, related_name='invoice_items', null=True, blank=True,
                                  help_text='Please chose the physican who is givng the medical prescription')


    def prestations_invoiced(self):
        return '%s prestations. Total = %s' % (
            len(self.prestations.all()), sum(a.net_amount for a in self.prestations.all()))

    def clean(self, *args, **kwargs):
        super(InvoiceItem, self).clean()
        if self.patient_id is not None and self.is_private != self.patient.is_private:
            raise ValidationError({'patient': 'Only private Patients allowed in private Invoice Item.'})

    @property
    def invoice_month(self):
        return self.invoice_date.strftime("%B %Y")

    def __get_patients_without_invoice(self, current_month):
        qinvoices_of_current_month = InvoiceItem.objects.filter(date__month=current_month.month)
        patients_pks_having_an_invoice = list()
        for i in qinvoices_of_current_month:
            patients_pks_having_an_invoice.append(i.patient.pk)
        return patients_pks_having_an_invoice

    def __unicode__(self):  # Python 3: def __str__(self):
        return 'invocie no.: %s - nom patient: %s' % (self.invoice_number, self.patient)


class Prestation(models.Model):
    invoice_item = models.ForeignKey(InvoiceItem, related_name='prestations')
    employee = models.ForeignKey('invoices.Employee', related_name='prestations', null=True, default=None)
    carecode = models.ForeignKey(CareCode, related_name='prestations')
    date = models.DateTimeField('date')
    date.editable = True

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
