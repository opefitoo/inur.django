from dataclasses import dataclass
from datetime import date

from django.core.exceptions import ValidationError
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
    # DateEnvoiPrestataire
    date_of_notification_to_provider = models.DateField(_("Date d'envoi au prestataire"))
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
    # date changement vers un nouveau plan
    date_of_change_to_new_plan = models.DateField(_("Date de changement vers un nouveau plan"), blank=True, null=True)

    # validate that there is no other plan that has a date_of_decision more recent than date_of_change_to_new_plan
    def validate_constraints(self, exclude=None):
        # if date_of_change_to_new_plan is not null
        # check that there is no other plan that has a date_of_decision more recent than date_of_change_to_new_plan
        if self.date_of_change_to_new_plan:
            if MedicalCareSummaryPerPatient.objects.filter(patient=self.patient,
                                                           date_of_decision__lte=self.date_of_change_to_new_plan).exists():
                conflict = MedicalCareSummaryPerPatient.objects.filter(patient=self.patient,
                                                                       date_of_decision__lte=self.date_of_change_to_new_plan).get()
                raise ValidationError(
                    _('Il existe déjà une synthèse de prise en charge avec une date de décision plus récente que la date de changement vers un nouveau plan: %s') % conflict)
        return True

    class Meta:
        unique_together = ('patient', 'plan_number', 'decision_number', 'date_of_decision')
        verbose_name = _("Synthèse de prise en charge par patient")
        verbose_name_plural = _("Synthèses de prise en charge par patient")

    def __str__(self):
        if self.date_of_change_to_new_plan:
            return "Synthèse de {0} en date du {1} jusque {2}".format(
                self.patient, self.date_of_decision, self.date_of_change_to_new_plan)
        return "Synthèse de prise en charge {0} en date du {1}".format(self.patient, self.date_of_decision)


@property
def is_latest_plan(self):
    # if self has most recent date_of_notification_to_provider then return True
    # else return False
    if self.date_of_notification_to_provider == MedicalCareSummaryPerPatient.objects.filter(
            patient=self.patient).latest('date_of_notification_to_provider').date_of_notification_to_provider:
        return True
    else:
        return False


# model Prestatations
class MedicalCareSummaryPerPatientDetail(models.Model):
    class Meta:
        verbose_name = _("Prestation Prestataire")
        verbose_name_plural = _("Prestations Prestataire")

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
    class Meta:
        verbose_name = _("Prestation Aidant")
        verbose_name_plural = _("Prestations Aidant")

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


@dataclass
class MedicalSummaryData:
    """Summary data for a single day."""
    start_date: date
    end_date: date
    medicalSummaryPerPatient: MedicalCareSummaryPerPatient


def get_summaries_between_two_dates(patient, start_date, end_date):
    summaries = MedicalCareSummaryPerPatient.objects.filter(patient=patient,
                                                            date_of_decision__lte=end_date,
                                                            date_of_decision__gte=start_date,
                                                            date_of_change_to_new_plan__gte=start_date) | \
                MedicalCareSummaryPerPatient.objects.filter(patient=patient,
                                                            date_of_decision__lte=end_date,
                                                            date_of_decision__gte=start_date,
                                                            date_of_change_to_new_plan__isnull=True).order_by(
                    "date_of_decision")
    summary_data = []
    for summary in summaries:
        if summary.date_of_decision < start_date and summary.date_of_change_to_new_plan:
            summary_data.append(MedicalSummaryData(medicalSummaryPerPatient=summary,
                                                   start_date=start_date,
                                                   end_date=summary.date_of_change_to_new_plan))
        elif summary.date_of_decision < start_date and not summary.date_of_change_to_new_plan:
            summary_data.append(MedicalSummaryData(medicalSummaryPerPatient=summary,
                                                   start_date=start_date,
                                                   end_date=end_date))
        elif summary.date_of_decision >= start_date and summary.date_of_change_to_new_plan:
            summary_data.append(MedicalSummaryData(medicalSummaryPerPatient=summary,
                                                   start_date=summary.date_of_decision,
                                                   end_date=summary.date_of_change_to_new_plan))
        elif summary.date_of_decision >= start_date and not summary.date_of_change_to_new_plan:
            summary_data.append(MedicalSummaryData(medicalSummaryPerPatient=summary,
                                                   start_date=summary.date_of_decision,
                                                   end_date=end_date))
    return summary_data
