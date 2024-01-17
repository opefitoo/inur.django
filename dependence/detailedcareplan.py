from dataclasses import dataclass
from datetime import date

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from dependence.cnscommunications import InformalCaregiverUnavailability
from dependence.enums.longtermcare_enums import UnavailabilityTypeChoices
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
    date_of_change_to_new_plan = models.DateField(_("Date de changement vers un nouveau plan"),
                                                  help_text="Date fin d'application du plan", blank=True, null=True)
    date_of_start_of_plan_for_us = models.DateField(_("Date début application du plan"), blank=True, null=True)

    # validate that there is no other plan that has a date_of_decision more recent than date_of_change_to_new_plan
    def validate_constraints(self, exclude=None):
        self.validate_date_of_start_of_plan_for_us_is_before_date_of_change_to_new_plan()
        self.validate_no_overlap_with_other_plans()

    def validate_date_of_start_of_plan_for_us_is_before_date_of_change_to_new_plan(self):
        if self.date_of_change_to_new_plan and self.date_of_start_of_plan_for_us:
            if self.date_of_start_of_plan_for_us > self.date_of_change_to_new_plan:
                raise ValidationError(
                    _('La date de début d\'application du plan doit être antérieure à la date de changement vers un nouveau plan'))
        return True

    def validate_no_overlap_with_other_plans(self):
        # check for overlaps
        for other in MedicalCareSummaryPerPatient.objects.filter(patient=self.patient,
                                                                 date_of_start_of_plan_for_us__isnull=False).exclude(
            id=self.id):
            # If other plan has no end date (is still ongoing)
            if other.date_of_change_to_new_plan is None:
                if self.date_of_start_of_plan_for_us > other.date_of_start_of_plan_for_us:
                    raise ValidationError('There is an overlap with another ongoing plan. %s' % other)
            else:
                # If current plan has no end date (is still ongoing)
                if self.date_of_change_to_new_plan is None:
                    if other.date_of_start_of_plan_for_us < self.date_of_start_of_plan_for_us < other.date_of_change_to_new_plan:
                        raise ValidationError('There is an overlap with another plan. %s' % other)
                # Both plans have start and end dates
                else:
                    if other.date_of_start_of_plan_for_us < self.date_of_start_of_plan_for_us < other.date_of_change_to_new_plan:
                        raise ValidationError('There is an overlap with another plan. %s' % other)
                    if other.date_of_start_of_plan_for_us < self.date_of_change_to_new_plan < other.date_of_change_to_new_plan:
                        raise ValidationError('There is an overlap with another plan. %s' % other)
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
    custom_description = models.TextField(max_length=500, blank=True, null=True)
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
    custom_description = models.TextField(max_length=500, blank=True, null=True)
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
    packageLevel: int = 0


def get_summaries_between_two_dates(patient, start_date, end_date):
    summaries = MedicalCareSummaryPerPatient.objects.filter(patient=patient,
                                                            date_of_decision__lte=end_date,
                                                            date_of_decision__gte=start_date,
                                                            date_of_change_to_new_plan__lte=end_date) | \
                MedicalCareSummaryPerPatient.objects.filter(patient=patient,
                                                            date_of_decision__lte=end_date,
                                                            date_of_change_to_new_plan__isnull=True) | \
                MedicalCareSummaryPerPatient.objects.filter(patient=patient,
                                                            date_of_change_to_new_plan__isnull=True,
                                                            date_of_start_of_plan_for_us__lte=end_date) | \
                MedicalCareSummaryPerPatient.objects.filter(patient=patient,
                                                            date_of_decision__gte=start_date,
                                                            date_of_decision__lte=end_date) | \
                MedicalCareSummaryPerPatient.objects.filter(patient=patient,
                                                            date_of_change_to_new_plan__gte=end_date,
                                                            date_of_start_of_plan_for_us__lte=start_date).order_by(
                    "date_of_decision")

    summary_data = []
    # check if there InformalCaregiverUnavailability linked to this patient for the period
    unavailability_start = InformalCaregiverUnavailability.objects.filter(patient=patient,
                                                                          unavailability_date__gte=start_date,
                                                                          unavailability_date__lte=end_date,
                                                                          unavailability_type=UnavailabilityTypeChoices.DEBUT).first()
    unavailability_end = InformalCaregiverUnavailability.objects.filter(patient=patient,
                                                                        unavailability_date__gte=end_date,
                                                                        unavailability_date__gt=start_date,
                                                                        unavailability_type=UnavailabilityTypeChoices.RETOUR).first()
    for summary in summaries:
        medical_start_date = None
        medical_end_date = end_date

        if not summary.date_of_start_of_plan_for_us and summary.date_of_decision < start_date:
            medical_start_date = start_date
        elif summary.date_of_decision >= start_date:
            medical_start_date = summary.date_of_decision
        elif summary.date_of_start_of_plan_for_us and summary.date_of_start_of_plan_for_us >= start_date:
            medical_start_date = summary.date_of_start_of_plan_for_us
        elif summary.date_of_start_of_plan_for_us and summary.date_of_start_of_plan_for_us <= start_date:
            medical_start_date = start_date

        if summary.date_of_change_to_new_plan and ((not summary.date_of_start_of_plan_for_us) or (
                summary.date_of_start_of_plan_for_us and summary.date_of_decision <= start_date)) and summary.date_of_change_to_new_plan <= end_date:
            medical_end_date = summary.date_of_change_to_new_plan
        else:
            medical_end_date = end_date
        if unavailability_start and not unavailability_end:
            package_level = summary.level_of_needs
            summary_data.append(MedicalSummaryData(medicalSummaryPerPatient=summary,
                                                   start_date=unavailability_start.unavailability_date,
                                                   end_date=medical_end_date,
                                                   packageLevel=package_level))
        elif unavailability_start and unavailability_end:
            package_level = summary.level_of_needs
            summary_data.append(MedicalSummaryData(medicalSummaryPerPatient=summary,
                                                   start_date=unavailability_start.unavailability_date,
                                                   end_date=unavailability_end.unavailability_date,
                                                   packageLevel=package_level))
        elif not unavailability_start and unavailability_end:
            package_level = summary.level_of_needs
            summary_data.append(MedicalSummaryData(medicalSummaryPerPatient=summary,
                                                   start_date=medical_start_date,
                                                   end_date=unavailability_end.unavailability_date,
                                                   packageLevel=package_level))
        else:
            package_level = summary.nature_package
            summary_data.append(MedicalSummaryData(medicalSummaryPerPatient=summary,
                                                   start_date=medical_start_date,
                                                   end_date=medical_end_date,
                                                   packageLevel=package_level))

    return summary_data
