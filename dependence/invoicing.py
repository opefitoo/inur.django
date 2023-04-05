from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from dependence.longtermcareitem import LongTermCareItem
from invoices.employee import Employee
from invoices.models import Patient


# décompte mensuel de factures
class LongTermCareMonthlyStatement(models.Model):
    class Meta:
        verbose_name = _("Décompte mensuel de factures")
        verbose_name_plural = _("Décomptes mensuels de factures")
    year = models.PositiveIntegerField(_('Year'))
    # invoice month
    month = models.PositiveIntegerField(_('Month'))
    generated_invoice_file = models.FileField(_('Generated Invoice File'), blank=True, null=True)
    force_regeneration = models.BooleanField(_('Force Regeneration'), default=False)
    # dateEnvoi
    date_of_submission = models.DateField(_('Date d\'envoi du fichier'), blank=True, null=True)
    # dateReception
    generated_invoice_file_response = models.FileField(_('Generated Invoice Response File'), blank=True, null=True)
    date_of_receipt = models.DateField(_('Date de réception du fichier'), blank=True, null=True)

    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def __str__(self):
        return f"{self.year} - {self.month}"


class LongTermCareInvoiceFile(models.Model):
    link_to_monthly_statement = models.ForeignKey(LongTermCareMonthlyStatement, on_delete=models.CASCADE,
                                                  related_name='monthly_statement', blank=True, null=True)
    # invoice year is positive integer
    invoice_start_period = models.DateField(_('Invoice Start Period'), )
    invoice_end_period = models.DateField(_('Invoice End Period'), )
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient')
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    # must be linked to a monthly statement that is same period as invoice file
    def clean(self):
        if self.link_to_monthly_statement.month != self.invoice_start_period.month:
            raise ValidationError("Le mois de la facture doit être le même que le mois du décompte mensuel")
        if self.link_to_monthly_statement.year != self.invoice_start_period.year:
            raise ValidationError("L'année de la facture doit être la même que l'année du décompte mensuel")
        if self.link_to_monthly_statement.month != self.invoice_end_period.month:
            raise ValidationError("Le mois de la facture doit être le même que le mois du décompte mensuel")
        if self.link_to_monthly_statement.year != self.invoice_end_period.year:
            raise ValidationError("L'année de la facture doit être la même que l'année du décompte mensuel")

    class Meta:
        verbose_name = _("Facture assurance dépendance")
        verbose_name_plural = _("Factures assurance dépendance")


    def __str__(self):
        return "Facture assurance dépendance de {0}/{1} patient {2}".format(self.invoice_start_period,
                                                                            self.invoice_end_period,
                                                                            self.patient)

    # on save gather all events for the month and generate the invoice file




class LongTermCareInvoiceItem(models.Model):
    INVOICE_ITEM_STATUS = (
        ('DONE', _('Done')),
        ('NOT_DONE', _('Not Done')),
        ('CANCELLED', _('Cancelled')),
    )
    invoice = models.ForeignKey(LongTermCareInvoiceFile, on_delete=models.CASCADE, related_name='invoice')
    item_date = models.DateField(_('Item Date'), )
    long_term_care_item = models.ForeignKey(LongTermCareItem, on_delete=models.CASCADE, related_name='long_term_care_item')
    assigned_employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='assigned_employee')
    status = models.CharField(_('Status'), max_length=100, choices=INVOICE_ITEM_STATUS, default='DONE')
    notes = models.TextField(_('Notes'), blank=True, null=True)
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    class Meta:
        verbose_name = _("Ligne de facture assurance dépendance")
        verbose_name_plural = _("Lignes de facture assurance dépendance")


# @receiver(post_save, sender=LongTermCareInvoiceFile, dispatch_uid="generate_invoice_file_and_notify_via_chat_5QH9cN")
# def parse_xml_and_notify_via_chat(sender, instance, **kwargs):
#     if instance.generated_invoice_file:
#         message = "Le fichier de facture %s a été mis à jour." % instance.generated_invoice_file
#     if instance.force_regeneration:
#         generate_invoice_file(instance)
#         notify_system_via_google_webhook(message)
#         return
