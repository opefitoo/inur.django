from django.db import models
from django.utils.translation import gettext_lazy as _

from dependence.longtermcareitem import LongTermCareItem
from invoices.models import Patient


class MedicalCareSummaryPerPatient(models.Model):

    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)
    # Fields
    # field patient
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_care_summary_per_patient')
    # DateDemande
    date_of_request = models.DateField(_("Date de demande"))
    # Referent
    referent = models.CharField(_("Référent"), max_length=50)
    # DateEvaluation
    date_of_evaluation = models.DateField(_("Date d'évaluation"))
    # DateNotification
    date_of_notification = models.DateField(_("Date de notification"))
    # NoPlan
    plan_number = models.CharField(_("Numéro de plan"), max_length=25)
    # NoDecision
    decision_number = models.CharField(_("Numéro de décision"), max_length=25)
    # Accord
    # NiveauBesoins chiffre
    level_of_needs = models.IntegerField(_("Niveau de besoins"))
    # DebutPriseEnCharge
    start_of_support = models.DateField(_("Début de prise en charge"))
    # FinPriseEnCharge
    end_of_support = models.DateField(_("Fin de prise en charge"), blank=True, null=True)
    # DateDecision
    date_of_decision = models.DateField(_("Date de décision"))
    # ForfaitSpecial (texte)
    special_package = models.CharField(_("Forfait spécial"), max_length=10, blank=True, null=True)
    # ForfaitPN (chiffre) Forfait Prestation en nature
    nature_package = models.IntegerField(_("Forfait Prestation en nature"), blank=True, null=True)
    # ForfaitPE (chiffre) Forfait Prestation en espèces
    cash_package = models.IntegerField(_("Forfait Prestation en espèces"), blank=True, null=True)
    # DroitFMI (booléen)
    fmi_right = models.BooleanField(_("Droit FMI"), default=False)
    # sn code of the helper
    sn_code_aidant = models.CharField(_("SN Code Aidant"), max_length=13, null=True, blank=True)

    # create a composite unique constraint
    class Meta:
        unique_together = ('patient', 'plan_number', 'decision_number', 'date_of_decision')
        verbose_name = _("Synthèse de prise en charge par patient")
        verbose_name_plural = _("Synthèses de prise en charge par patient")

    def __str__(self):
        return "Synthèse de prise en charge du patient {0}".format(self.patient)


# model Prestatations
class MedicalCareSummaryPerPatientDetail(models.Model):
    # Fields
    # field patient
    # one to one relation to LongTermCareItem
    item = models.ForeignKey(LongTermCareItem, on_delete=models.CASCADE,
                             related_name='medical_care_summary_per_patient_detail_item')
    # many to one relation to MedicalCareSummaryPerPatient
    medical_care_summary_per_patient = models.ForeignKey(MedicalCareSummaryPerPatient, on_delete=models.CASCADE,
                                                         related_name='medical_care_summary_per_patient_detail')
    # number of care
    number_of_care = models.IntegerField(_("Fréquence"))
    # périodicité
    periodicity = models.CharField(_("Périodicité"), max_length=15, choices=(
        ('D', _('Daily')),
        ('W', _('Weekly')),
        ('M', _('Monthly')),
        ('A', _('Annually')),))
    def __str__(self):
        # code de l'acte / fréquence / périodicité
        return " {0} / {1} / {2}".format(self.item.code, self.number_of_care, self.periodicity)


class SharedMedicalCareSummaryPerPatientDetail(models.Model):

    item = models.ForeignKey(LongTermCareItem, on_delete=models.CASCADE,
                             related_name='shared_medical_care_summary_per_patient_detail_item')
    # many to one relation to MedicalCareSummaryPerPatient
    medical_care_summary_per_patient = models.ForeignKey(MedicalCareSummaryPerPatient, on_delete=models.CASCADE,
                                                         related_name='shared_medical_care_summary_per_patient_detail')
    # number of care
    number_of_care = models.IntegerField(_("Fréquence"))
    # périodicité
    periodicity = models.CharField(_("Périodicité"), max_length=15, choices=(
        ('D', _('Daily')),
        ('W', _('Weekly')),
        ('M', _('Monthly')),
        ('A', _('Annually')),))

    def __str__(self):
        # code de l'acte / fréquence / périodicité
        return " {0} / {1} / {2}".format(self.item.code, self.number_of_care, self.periodicity)
