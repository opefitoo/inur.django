import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
import pytz

# from invoices.widgets import MyAdminSplitDateTime
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
    phone_number = models.CharField(max_length=30)
    email_address = models.EmailField(default=None, blank=True, null=True)
    participation_statutaire = models.BooleanField()
    # TODO: rename to is_private
    private_patient = models.BooleanField(default=False)

    def get_patients_that_have_prestations(self, monthyear):
        ##XXX use this later for raw sql
        #         Patient.objects.raw("select p.name, p.first_name "
        #         + " from public.invoices_patient p, public.invoices_prestation prest"
        #         + " where p.id = prest.patient_id"
        #         + " and prest.date between '2013-10-01'::DATE and '2013-10-31'::DATE group by p.id" % (start_date, end_date)

        patients_sans_facture = Patient.objects.raw("select p.name, p.first_name " +
                                                    "from public.invoices_patient p, public.invoices_prestation prest " +
                                                    "where p.id = prest.patient_id " +
                                                    "and prest.date between '2013-10-01'::DATE and '2013-10-31'::DATE " +
                                                    "and (select count(inv.id) from public.invoices_invoiceitem inv " +
                                                    "where inv.invoice_date between '2013-10-01'::DATE and '2013-10-31'::DATE " +
                                                    "and inv.patient_id = p.id) = 0 " +
                                                    "group by p.id " +
                                                    "order by p.name")
        return patients_sans_facture

    def __unicode__(self):  # Python 3: def __str__(self):
        return '%s %s' % (self.name.strip(), self.first_name.strip())


# TODO: 1. can maybe be extending common class with Patient ?
# TODO: 2. synchronize physician details with Google contacts
class Physician(models.Model):
    code_sn = models.CharField(max_length=30)
    first_name = models.CharField(max_length=30)
    name = models.CharField(max_length=30)
    address = models.TextField(max_length=30)
    zipcode = models.CharField(max_length=10)
    city = models.CharField(max_length=30)
    phone_number = models.CharField(max_length=30)
    email_address = models.EmailField(default=None, blank=True, null=True)

    def __unicode__(self):  # Python 3: def __str__(self):
        return '%s %s' % (self.name.strip(), self.first_name.strip())


def get_default_invoice_number():
    # for _last_invoice in InvoiceItem.objects.all().order_by("-invoice_number")[0]:
    try:
        max1 = int(InvoiceItem.objects.all().order_by("-id")[0].invoice_number)
    except:
        max1 = 0

    return max(max1) + 1


class InvoiceItem(models.Model):
    invoice_number = models.CharField(max_length=50, default=get_default_invoice_number)
    accident_id = models.CharField(max_length=30, help_text=u"Numero d'accident est facultatif", null=True, blank=True)
    accident_date = models.DateField(help_text=u"Date d'accident est facultatif", null=True, blank=True)
    invoice_date = models.DateField('Invoice date')
    patient_invoice_date = models.DateField('Date envoi au patient  ')
    invoice_send_date = models.DateField('Date envoi facture', null=True, blank=True)
    invoice_sent = models.BooleanField()
    invoice_paid = models.BooleanField()
    medical_prescription_date = models.DateField('Date ordonnance', null=True, blank=True)
    patient = models.ForeignKey(Patient, related_name='patient',
                                help_text='choisir parmi ces patients pour le mois precedent')

    # TODO: I would like to store the file Field in Google drive
    # maybe this can be helpful https://github.com/torre76/django-googledrive-storage
    # upload_scan_medical_prescription = models.FileField()

    physician = models.ForeignKey(Physician, related_name='physician', null=True, blank=True,
                                  help_text='Please chose the physican who is givng the medical prescription')

    # TODO: when checked only patient which private_patient = true must be looked up via the ajax search lookup
    is_private = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super(InvoiceItem, self).save(*args, **kwargs)
        pytz_chicago = pytz.timezone("America/Chicago")
        if self.pk is not None:
            prestationsq = Prestation.objects.filter(
                Q(date__month=self.invoice_date.month - 1) | Q(date__month=self.invoice_date.month) | Q(
                    date__month=self.invoice_date.month + 1)).filter(date__year=self.invoice_date.year).filter(
                patient__pk=self.patient.pk)
            for p in prestationsq:
                normalized_date = pytz_chicago.normalize(p.date)
                if normalized_date.month == self.invoice_date.month:
                    self.prestations.add(p)
            super(InvoiceItem, self).save(*args, **kwargs)

    def prestations_invoiced(self):
        return '%s prestations. Total = %s' % (
            len(self.prestations.all()), sum(a.net_amount for a in self.prestations.all()))

    @property
    def invoice_month(self):
        return self.invoice_date.strftime("%B %Y")

    def __get_patients_without_invoice(self, current_month):
        qinvoices_of_current_month = InvoiceItem.objects.filter(date__month=current_month.month)
        patients_pks_having_an_invoice = list()
        for i in qinvoices_of_current_month:
            patients_pks_having_an_invoice.append(i.patient.pk)
        return patients_pks_having_an_invoice

    def clean(self, *args, **kwargs):
        # # don't allow patient to have more than one invoice for a month
        # import pydevd; pydevd.settrace()
        if hasattr(self, 'patient') and hasattr(self, 'invoice_date') and self.invoice_date is not None:
            iq = InvoiceItem.objects.filter(patient__pk=self.patient.pk).filter(
                Q(invoice_date__month=self.invoice_date.month) & Q(invoice_date__year=self.invoice_date.year)
            )
            prestationsq = Prestation.objects.filter(date__month=self.invoice_date.month).filter(
                date__year=self.invoice_date.year).filter(patient__pk=self.patient.pk)
            if not prestationsq.exists():
                raise ValidationError(
                    'Cannot create an invoice for this perdiod ''%s ''  for this patient ''%s'' because there were no medical service ' % (
                        self.invoice_date.strftime('%B-%Y'), self.patient))
            invoice_items = InvoiceItem.objects.filter(invoice_number=self.invoice_number)
            if invoice_items.exists():
                for invoice in invoice_items:
                    if invoice.pk != self.pk:
                        raise ValidationError('Already an invoice with this number ''%s ''  ' % self.invoice_number)
        super(InvoiceItem, self).clean()

    def __unicode__(self):  # Python 3: def __str__(self):
        return 'invocie no.: %s - nom patient: %s' % (self.invoice_number, self.patient)


class Prestation(models.Model):
    invoice_item = models.ForeignKey(InvoiceItem)
    carecode = models.ForeignKey(CareCode)
    date = models.DateTimeField('date')
    date.editable = True

    # TODO retrieve private_patient from Patient or compute it in a different way
    @property
    def net_amount(self):
        if not self.patient.private_patient:
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
        return 'code: %s - nom : %s' % (self.carecode.code, self.carecode.name)
