from django.db import models
from invoices.db.fields import CurrentUserField
from dependence.enums.falldeclaration_enum import (
    FallCircumstances,
    FallCognitiveMoodDiorders,
    FallConsequences,
    FallIncontinences,
    FallMedicationsRiskFactors,
    FallRequiredMedicalActs,
    FallmMbilityDisability
)

from invoices.models import Patient
from constance import config

from invoices.employee import Employee
from django.core.exceptions import ValidationError
import os
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_delete

from django import template

register = template.Library()

def update_fall_declaration_filename(instance, filename):
    file_name, file_extension = os.path.splitext(filename)
    if instance.datetimeOfFall is None:
        _current_yr_or_prscr_yr = now().date().strftime('%Y')
        _current_month_or_prscr_month = now().date().strftime('%M')
    else:
        _current_yr_or_prscr_yr = str(instance.datetimeOfFall.year)
        _current_month_or_prscr_month = str(instance.datetimeOfFall.month)
    path = os.path.join("Fall_Declaration", _current_yr_or_prscr_yr,
                        _current_month_or_prscr_month)
    filename = '%s_%s_%s_%s%s' % ( instance.patient.name, instance.patient.first_name,
                                instance.patient.code_sn,
                                str(instance.datetimeOfFall), file_extension)

    return os.path.join(path, filename)


def validate_file(file):
    try:
        file_size = file.file.size
    except:
        return
    limit_kb = 10
    if file_size > limit_kb * 1024 * 1024:
        raise ValidationError(_("Maximum file size is %s MB" % limit_kb))

class FallDeclaration(models.Model):
    class Meta:
        ordering = ["patient__id"]
        verbose_name = _("Fall Declaration")
        verbose_name_plural = _("Fall Declarations")

    patient = models.ForeignKey(
        Patient,
        help_text=_("Only looks for patients covered by long-term care insurance, check that the checkbox is validated if you cannot find your patient"),
        related_name="falldeclaration_to_patient",
        on_delete=models.CASCADE,
        limit_choices_to={"is_under_dependence_insurance": True},
    )
    datetimeOfFall = models.DateTimeField(_("Date, time of fall"))
    placeOfFall = models.CharField(_("Place of fall"), max_length=200)

    declared_by = models.ForeignKey(
        Employee,
        verbose_name=_("Declared by"),
        limit_choices_to=~models.Q(abbreviation__in=["XXX"]),
        related_name="edeclaring_employee",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        default=None,
    )
    file_upload = models.FileField(_("Attached file"),null=True, blank=True, upload_to=update_fall_declaration_filename,
                              validators=[validate_file],
                              help_text= _("You can attach the scan of the declaration"))
    witnesses = models.CharField(
        _("Possible witnesses"), max_length=255, null=True, blank=True, default=None
    )
    fall_circumstance = models.CharField(
        _("Circumstances of the fall"), choices=FallCircumstances.choices, max_length=255
    )
    other_fall_circumstance = models.CharField(
        _("Other circumstances of the fall"),
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )
    incident_circumstance = models.TextField(
        _("Circumstances of the incident"),
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )
    fall_consequences = models.CharField(
        _("Consequences of the fall"), 
        choices=FallConsequences.choices,
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )
    other_fall_consequence = models.CharField(
        _("Other consequence of the fall"),
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )
    fall_required_medical_acts = models.CharField(
        _("Medical and/or nursing acts required within 24 hoursonsequences of the fall"),
        choices=FallRequiredMedicalActs.choices,
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )
    other_required_medical_act = models.CharField(
        _("Other medical and/or nursing acts required within 24 hours"),
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )
    medications_risk_factor = models.CharField(
        _("Risk factors"), max_length=255, null=True, blank=True, default=None,
        choices=FallMedicationsRiskFactors.choices
    )
    fall_cognitive_mood_diorders = models.CharField(
        _("Cognitive and/or mood disorders"),
        choices=FallCognitiveMoodDiorders.choices,
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )
    fall_incontinences = models.CharField(
        _("Incontinence"),
        choices=FallIncontinences.choices,
        max_length=255,
        null=True,
        blank=True,
        default=None,
    )
    mobility_disability = models.CharField(_("Mobility Disability"), choices=FallmMbilityDisability.choices,
                                            max_length=255)
    unsuitable_footwear = models.BooleanField(_("Unsuitable footwear"), default=False)
    other_contributing_factor = models.TextField(
        _("Other contributing factor"), max_length=255, null=True, blank=True, default=None
    )
    preventable_fall = models.BooleanField(_("The fall could have been prevented"))
    physician_informed = models.BooleanField(_("The doctor was notified"))
    # Technical Fields
    created_on = models.DateTimeField(_("Created on"), auto_now_add=True)
    updated_on = models.DateTimeField(_("Last update"), auto_now=True)
    user = CurrentUserField(verbose_name=_("Created by"))

    @property
    def header_details(self):
        return [
            config.NURSE_NAME,
            config.MAIN_NURSE_CODE,
            config.NURSE_ADDRESS,
            config.NURSE_ZIP_CODE_CITY,
            config.NURSE_PHONE_NUMBER,
        ]


@receiver(post_delete, sender=FallDeclaration, dispatch_uid="fall_decaration_file_upload_clean_s3_post_delete")
def fall_decaration_file_upload_clean_s3_post_delete(sender, instance, **kwargs):
    if instance.file_upload:
        instance.file_upload.delete(save=False)

@receiver(pre_save, sender=FallDeclaration, dispatch_uid="fall_decaration_file_upload_clean_s3_pre_save")
def fall_decaration_file_upload_clean_s3_pre_save(sender, instance, **kwargs):
    if instance._get_pk_val() and instance.file_upload.name:
        old_file_name=instance.file_upload.name
        new_file_name=update_fall_declaration_filename(instance,old_file_name)
        if (old_file_name != new_file_name):
            my_file = instance.file_upload.storage.open(old_file_name, 'rb')
            instance.file_upload.storage.save(new_file_name,my_file)
            my_file.close()
            instance.file_upload.delete(save=False)
            instance.file_upload.name=new_file_name
