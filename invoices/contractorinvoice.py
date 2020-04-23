from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import IntegerField, Max, Q
from django.db.models.functions import Cast
from django_countries.fields import CountryField

from invoices.models import Patient, MedicalPrescription


def get_default_contractor_invoice_number():
    default_invoice_number = 0
    max_invoice_number = ContractorInvoiceItem.objects.filter(Q(invoice_number__iregex=r'^\d+$')).annotate(
        invoice_number_int=Cast('invoice_number', IntegerField())).aggregate(Max('invoice_number_int'))

    if max_invoice_number['invoice_number_int__max'] is not None:
        default_invoice_number = max_invoice_number['invoice_number_int__max']

    default_invoice_number += 1

    return default_invoice_number


class Contractor(models.Model):
    class Meta(object):
        verbose_name = u"Sous traitant"
        verbose_name_plural = u"Sous traitants"

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

    def __str__(self):
        return '%s %s' % (self.first_name, self.name)


class SalesCommissions(models.Model):
    """
    """

    class Meta:
        ordering = ['-id']

    start_date = models.DateField("date debut validite")
    end_date = models.DateField("date fin validite", blank=True, null=True)
    discount = models.DecimalField("montant brut", max_digits=5, decimal_places=2)
    contractor = models.ForeignKey(Contractor
                                   , related_name='contractor_discounts'
                                   , on_delete=models.CASCADE)

    def __str__(self):
        return 'from %s to %s' % (self.start_date, self.end_date)

    def clean(self, *args, **kwargs):
        exclude = []
        if self.care_code is not None and self.care_code.id is None:
            exclude = ['care_code']

        super(SalesCommissions, self).clean_fields(exclude)
        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(SalesCommissions.validate_dates(data))

        return result

    @staticmethod
    def validate_dates(data):
        messages = {}
        is_valid = data['end_date'] is None or data['start_date'] <= data['end_date']
        if not is_valid:
            messages = {'end_date': 'End date must be bigger than Start date'}

        return messages


class ContractorInvoiceItem(models.Model):
    class Meta(object):
        verbose_name = u"Mémoire d'honoraire"
        verbose_name_plural = u"Mémoires d'honoraire"

    PRESTATION_LIMIT_MAX = 20

    invoice_number = models.CharField(max_length=50, unique=True, default=get_default_contractor_invoice_number)
    is_private = models.BooleanField('Facture pour patient non pris en charge par CNS',
                                     help_text=u'Seuls les patients qui ne disposent pas de la prise en charge CNS '
                                               u'seront recherchés dans le champ Patient (privé)',
                                     default=False)
    patient = models.ForeignKey(Patient, related_name='invoice_items',
                                help_text=u"choisir parmi les patients en entrant quelques lettres de son nom ou prénom",
                                on_delete=models.CASCADE)
    subcontractor = models.ForeignKey(Contractor, related_name='invoice_subcontractor',
                                      help_text=u'Si vous introduisez un sous traitant',
                                      on_delete=models.CASCADE, null=True, blank=True)
    accident_id = models.CharField(max_length=30, help_text=u"Numéro d'accident est facultatif", null=True, blank=True)
    accident_date = models.DateField(help_text=u"Date d'accident est facultatif", null=True, blank=True)
    invoice_date = models.DateField('Invoice date')
    patient_invoice_date = models.DateField('Date envoi au patient', null=True, blank=True)
    invoice_send_date = models.DateField('Date envoi facture', null=True, blank=True)
    invoice_sent = models.BooleanField(default=False)
    invoice_paid = models.BooleanField(default=False)
    is_valid = models.BooleanField(default=True)
    validation_comment = models.TextField(null=True, blank=True)
    medical_prescription = models.ForeignKey(MedicalPrescription, related_name='invoice_items', null=True, blank=True,
                                             help_text='Please chose a Medical Prescription', on_delete=models.SET_NULL)

    def clean(self, *args, **kwargs):
        super(ContractorInvoiceItem, self).clean_fields()
        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        result.update(ContractorInvoiceItem.validate_is_private(data))
        result.update(ContractorInvoiceItem.validate_patient(data))

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
