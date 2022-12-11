from django.db import models
from invoices.db.fields import CurrentUserField
from dependence.enums.falldecleration_enum import (
    FallCircumstances,
    FallConsequences,
    FallRequiredMedicalActs,
    FallMedicationsRiskFactors,
    FallCognitiveMoodDiorders,
    FallIncontinences,
    FallmMbilityDisability
)

from invoices.models import Patient
from constance import config

from invoices.employee import Employee
from django.core.exceptions import ValidationError
import os
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _

def update_fall_decleration_filename(instance, filename):
    file_name, file_extension = os.path.splitext(filename)
    if instance.date is None:
        _current_yr_or_prscr_yr = now().date().strftime('%Y')
        _current_month_or_prscr_month = now().date().strftime('%M')
    else:
        _current_yr_or_prscr_yr = str(instance.date.year)
        _current_month_or_prscr_month = str(instance.date.month)
    path = os.path.join("Fall Decleration", _current_yr_or_prscr_yr,
                        _current_month_or_prscr_month)
    filename = '%s_%s_%s%s' % ( instance.patient.name, instance.patient.first_name,
                                       str(instance.datetimeOfFall), file_extension)

    return os.path.join(path, filename)


def validate_file(file):
    try:
        file_size = file.file.size
    except:
        return
    limit_kb = 10
    if file_size > limit_kb * 1024 * 1024:
        raise ValidationError("Taille maximale du fichier est %s MO" % limit_kb)

class FallDecleration(models.Model):
    class Meta:
        ordering = ["patient__id"]
        verbose_name = "Fall Decleration"
        verbose_name_plural = "Fall Decleration"

    patient = models.ForeignKey(
        Patient,
        help_text="Ne recheche que les patients pris en charge par l'assurance dépendance, vérifiez que la checkbox est validé si vous ne trouvez pas votre patient",
        related_name="falldecleration_to_patient",
        on_delete=models.CASCADE,
        limit_choices_to={"is_under_dependence_insurance": True},
    )
    datetimeOfFall = models.DateTimeField("Date, heure de la chute")
    placeOfFall = models.CharField("Lieu de la chute", max_length=200)

    declared_by = models.ForeignKey(
        Employee,
        verbose_name="Déclaré par",
        limit_choices_to=~models.Q(abbreviation__in=["XXX"]),
        related_name="edeclaring_employee",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        default=None,
    )
    file_upload = models.FileField(null=True, blank=True, upload_to=update_fall_decleration_filename,
                              validators=[validate_file],
                              help_text= _("Vous pouvez attacher le scan de la déclaration"))
    witnesses = models.CharField(
        "Témoins éventuels", max_length=255, null=True, blank=True, default=None
    )
    fall_circumstance = models.CharField(
        "Circonstances de la chute", choices=FallCircumstances.choices, max_length=255
    )
    other_fall_circumstance = models.CharField(
        "Autre circonstances de la chute",
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )
    incident_circumstance = models.TextField(
        "Circonstances de l’incident",
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )
    other_fall_consequence = models.CharField(
        "Autre conséquence de la chute",
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )
    other_required_medical_act = models.CharField(
        "Autres actes médicaux et/ou infirmiers requis dans les 24h",
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )
    medications_risk_factor = models.CharField(
        "Facteurs de risque", max_length=255, null=True, blank=True, default=None,
        choices=FallMedicationsRiskFactors.choices
    )
    
    mobility_disability = models.CharField("Incapacité concernant les déplacements", choices=FallmMbilityDisability.choices,
                                            max_length=255)
    unsuitable_footwear = models.BooleanField("Chaussures inadaptées", default=False)
    other_contributing_factor = models.TextField(
        "Autre facteur favorisant", max_length=255, null=True, blank=True, default=None
    )
    preventable_fall = models.BooleanField("La chute aurait pu être prévenue")
    physician_informed = models.BooleanField("Le médecin a été avisé")
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)
    user = CurrentUserField(verbose_name="Créé par")

    @property
    def header_details(self):
        return [
            config.NURSE_NAME,
            config.MAIN_NURSE_CODE,
            config.NURSE_ADDRESS,
            config.NURSE_ZIP_CODE_CITY,
            config.NURSE_PHONE_NUMBER,
        ]


class FallConsequence(models.Model):
    fall_decleration = models.ForeignKey(
        FallDecleration, related_name="fall_consequences",
        on_delete=models.CASCADE,
    )
    consequence = models.CharField(choices=FallConsequences.choices, max_length=255)


class FallRequiredMedicalAct(models.Model):
    fall_decleration = models.ForeignKey(
        FallDecleration, related_name="fall_required_medical_acts",
        on_delete=models.CASCADE,
    )
    required_medical_act = models.CharField(choices=FallRequiredMedicalActs.choices,
        max_length=255)

class FallCognitiveMoodDiorder(models.Model):
    fall_decleration = models.ForeignKey(
        FallDecleration, related_name="fall_cognitive_mood_diorders",
        on_delete=models.CASCADE,
    )
    cognitive_mood_diorder = models.CharField(
        "Troubles cognitifs et/ou de l’humeur",
        choices=FallCognitiveMoodDiorders.choices,
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )

class FallIncontinence (models.Model):
    fall_decleration = models.ForeignKey(
        FallDecleration, related_name="fall_incontinences",
        on_delete=models.CASCADE,
    )
    incontinence = models.CharField(
        "Incontinence", max_length=255, null=True, blank=True, default=None,
        choices=FallIncontinences.choices
    )

