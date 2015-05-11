import logging

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
import pytz


# from invoices.widgets import MyAdminSplitDateTime
logger = logging.getLogger(__name__)

# Create your models here.
class CareCode(models.Model):
    code = models.CharField(max_length=30)
    name = models.CharField(max_length=50)
    description = models.TextField(max_length=100)
    # prix net = 88% du montant brut
    # prix brut
    gross_amount = models.DecimalField("montant brut", max_digits=5, decimal_places=2)
    #previous_gross_amount = models.DecimalField("Ancien montant brut", max_digits=5, decimal_places=2)
    #price_switch_date = models.DateField( help_text=u"Date d'accident est facultatif", null=True, blank=True)
    
    def __unicode__(self):  # Python 3: def __str__(self):
        return '%s: %s' % (self.code, self.name) 
    
class Patient(models.Model):
    code_sn = models.CharField(max_length=30)
    first_name = models.CharField(max_length=30)
    name = models.CharField(max_length=30)
    address = models.TextField(max_length=30)
    zipcode = models.CharField(max_length=10)
    city = models.CharField(max_length=30)
    phone_number = models.CharField(max_length=30)
    participation_statutaire = models.BooleanField()
    private_patient = models.BooleanField( default=False )
    
    def get_patients_that_have_prestations(self, monthyear):
        ##XXX use this later for raw sql
#         Patient.objects.raw("select p.name, p.first_name " 
#         + " from public.invoices_patient p, public.invoices_prestation prest"
#         + " where p.id = prest.patient_id"
#         + " and prest.date between '2013-10-01'::DATE and '2013-10-31'::DATE group by p.id" % (start_date, end_date)
        
        patients_sans_facture = Patient.objects.raw("select p.name, p.first_name "+  
        "from public.invoices_patient p, public.invoices_prestation prest "+
        "where p.id = prest.patient_id "+
        "and prest.date between '2013-10-01'::DATE and '2013-10-31'::DATE "+ 
        "and (select count(inv.id) from public.invoices_invoiceitem inv "+
        "where inv.invoice_date between '2013-10-01'::DATE and '2013-10-31'::DATE "+ 
        "and inv.patient_id = p.id) = 0 "+
        "group by p.id "+
        "order by p.name")
        return patients_sans_facture
       
    def __unicode__(self):  # Python 3: def __str__(self):
        return '%s %s' % ( self.name.strip() , self.first_name.strip() )
    
class Prestation(models.Model):
    patient = models.ForeignKey(Patient)
    carecode = models.ForeignKey(CareCode)
    date = models.DateTimeField('date')
#     formfield_overrides = {
#         models.DateTimeField: {'widget': MyAdminSplitDateTime},
#     }
    @property   
    def net_amount(self):
        "Returns the net amount"
        #normalized_price_switch_date = pytz_chicago.normalize( self.carecode.price_switch_date )
        #if self.date > normalized_price_switch_date:
            # round to only two decimals
         #   return round(((self.carecode.gross_amount * 88) / 100), 2)
        # round to only two decimals
        #return round(((self.carecode.previous_gross_amount * 88) / 100), 2)
        return round(((self.carecode.gross_amount * 88) / 100) , 2) + self.fin_part 

    @property   
    def fin_part(self):
        "Returns the financial participation of the client"
        #pytz_chicago = pytz.timezone("America/Chicago")
        #normalized_price_switch_date = pytz_chicago.normalize( self.carecode.price_switch_date )
        if self.patient.participation_statutaire:
            return 0
        # round to only two decimals
        #if self.date > normalized_price_switch_date:
        #    return round(((self.carecode.gross_amount * 12) / 100), 2)
        return round(((self.carecode.gross_amount * 12) / 100), 2)
    
    def clean(self):
        "if same prestation same date same code same patient, disallow creation"
        prestationsq = Prestation.objects.filter(date=self.date).filter(patient__pk=self.patient.pk).filter(carecode__pk=self.carecode.pk)
        if prestationsq.exists():
            for presta_in_db in prestationsq:
                if(presta_in_db.pk != self.pk):
                    raise ValidationError('Cannot create medical service "code:%s on:%s for:%s" because is already exists' % (self.carecode,
                                                                                                                              self.date.strftime('%d-%m-%Y'),
                                                                                                                              self.patient ))
    
    def __unicode__(self):  # Python 3: def __str__(self):
        return 'code: %s - nom patient: %s' % (self.carecode.code , self.patient.name)

def get_default_invoice_number():
    #for _last_invoice in InvoiceItem.objects.all().order_by("-invoice_number")[0]:
    try:
        max1 = int(InvoiceItem.objects.all().order_by("-invoice_number")[0].invoice_number)
    except:
        max1 = 0
    #for _last_private_invoice in PrivateInvoiceItem.objects.all().order_by("-invoice_number")[0]:
    try:
        max2 = int (PrivateInvoiceItem.objects.all().order_by("-invoice_number")[0].invoice_number)
    except:
        max2 = 0
    return max(max1, max2) + 1
    
class InvoiceItem(models.Model):
    invoice_number = models.CharField(max_length=50, default = get_default_invoice_number)
    accident_id = models.CharField(max_length=30, help_text=u"Numero d'accident est facultatif", null=True, blank=True)
    accident_date = models.DateField( help_text=u"Date d'accident est facultatif", null=True, blank=True)
    invoice_date = models.DateField('Invoice date')
    invoice_sent = models.BooleanField()
    invoice_paid = models.BooleanField()
    medical_prescription_date = models.DateField('Date ordonnance', null=True, blank=True)
    patient = models.ForeignKey(Patient, related_name='patient', help_text='choisir parmi ces patients pour le mois precedent')
    prestations = models.ManyToManyField(Prestation, related_name='prestations', editable=False, blank=True)
    
    def save(self, *args, **kwargs):
        super(InvoiceItem, self).save(*args, **kwargs)
        pytz_chicago = pytz.timezone("America/Chicago")
        if self.pk is not None:
            #import pydevd; pydevd.settrace()
            prestationsq = Prestation.objects.filter(Q(date__month=self.invoice_date.month-1) | Q(date__month=self.invoice_date.month) | Q(date__month=self.invoice_date.month+1)).filter(date__year=self.invoice_date.year).filter(patient__pk=self.patient.pk)
            for p in prestationsq:
                normalized_date = pytz_chicago.normalize(p.date)
                if normalized_date.month == self.invoice_date.month:
                    self.prestations.add(p)                
            super(InvoiceItem, self).save(*args, **kwargs)
    
    def prestations_invoiced(self):
        return '%s prestations. Total = %s' % (len(self.prestations.all()), sum(a.net_amount for a in self.prestations.all()))
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
        #import pydevd; pydevd.settrace()
        if hasattr(self, 'patient') and hasattr(self, 'invoice_date') and self.invoice_date is not None:
            iq = InvoiceItem.objects.filter(patient__pk=self.patient.pk).filter(
                                                                                Q(invoice_date__month=self.invoice_date.month) & Q(invoice_date__year=self.invoice_date.year)
                                                                                )
            if iq.exists():
                for presta_in_db in iq:
                    if(presta_in_db.pk != self.pk):
                        raise ValidationError('Patient %s has already an invoice for the month ''%s'' ' % (self.patient , self.invoice_date.strftime('%B')))
            prestationsq = Prestation.objects.filter(date__month=self.invoice_date.month).filter(date__year=self.invoice_date.year).filter(patient__pk=self.patient.pk)
            if not prestationsq.exists():
                raise ValidationError('Cannot create an invoice for this perdiod ''%s ''  for this patient ''%s'' because there were no medical service ' % (self.invoice_date.strftime('%B-%Y'),  self.patient))
            invoice_items = InvoiceItem.objects.filter(invoice_number=self.invoice_number)
            if invoice_items.exists():
                for invoice in invoice_items:
                    if invoice.pk != self.pk:
                        raise ValidationError( 'Already an invoice with this number ''%s ''  ' % self.invoice_number)
        super(InvoiceItem, self).clean()

    def __unicode__(self):  # Python 3: def __str__(self):
        return 'invocie no.: %s - nom patient: %s' % (self.invoice_number , self.patient)
    
class PrivateInvoiceItem(models.Model):
    invoice_number = models.CharField(max_length=50, default = get_default_invoice_number)
    accident_id = models.CharField(max_length=30, help_text=u"Numero d'accident est facultatif", null=True, blank=True)
    accident_date = models.DateField( help_text=u"Date d'accident est facultatif", null=True, blank=True)
    invoice_date = models.DateField('Date facture')
    invoice_send_date = models.DateField('Date envoi facture', null=True, blank=True)
    medical_prescription_date = models.DateField('Date ordonnance', null=True, blank=True)
    invoice_sent = models.BooleanField()
    invoice_paid = models.BooleanField()
    private_patient = models.ForeignKey(Patient, related_name='private_invoice_patient', help_text='choisir parmi ces patients pour le mois precedent')
    prestations = models.ManyToManyField(Prestation, related_name='private_invoice_prestations', editable=False, blank=True)
    
    def save(self, *args, **kwargs):
        super(PrivateInvoiceItem, self).save(*args, **kwargs)
        pytz_chicago = pytz.timezone("America/Chicago")
        if self.pk is not None:
            prestationsq = Prestation.objects.raw("select prestations.id from invoices_prestation prestations "+
                                                  "where prestations.patient_id = %s " %(self.private_patient.pk) + 
                                                  "and prestations.id not in ( " +
                                                  "select pp.prestation_id "+ 
                                                  "from public.invoices_privateinvoiceitem priv, public.invoices_privateinvoiceitem_prestations pp "+
                                                  "group by pp.prestation_id)" )
            for p in prestationsq:
                self.prestations.add(p)
            super(PrivateInvoiceItem, self).save(*args, **kwargs)
    
    def prestations_invoiced(self):
        return '%s prestations. Total = %s' % (len(self.prestations.all()), sum(a.net_amount for a in self.prestations.all()))
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
        #import pydevd; pydevd.settrace()
        if hasattr(self, 'patient') and hasattr(self, 'invoice_date') and self.invoice_date is not None:
            iq = InvoiceItem.objects.filter(patient__pk=self.patient.pk).filter(
                                                                                Q(invoice_date__month=self.invoice_date.month) & Q(invoice_date__year=self.invoice_date.year)
                                                                                )
            if iq.exists():
                for presta_in_db in iq:
                    if(presta_in_db.pk != self.pk):
                        raise ValidationError('Patient %s has already an invoice for the month ''%s'' ' % (self.patient , self.invoice_date.strftime('%B')))
            prestationsq = Prestation.objects.filter(date__month=self.invoice_date.month).filter(date__year=self.invoice_date.year).filter(patient__pk=self.patient.pk)
            if not prestationsq.exists():
                raise ValidationError('Cannot create an invoice for this perdiod ''%s ''  for this patient ''%s'' because there were no medical service ' % (self.invoice_date.strftime('%B-%Y'),  self.patient))
            invoice_items = InvoiceItem.objects.filter(invoice_number=self.invoice_number)
            if invoice_items.exists():
                for invoice in invoice_items:
                    if invoice.pk != self.pk:
                        raise ValidationError( 'Already an invoice with this number ''%s ''  ' % self.invoice_number)
        super(PrivateInvoiceItem, self).clean()

    def __unicode__(self):  # Python 3: def __str__(self):
        return 'invocie no.: %s - nom patient: %s' % (self.invoice_number , self.private_patient)
