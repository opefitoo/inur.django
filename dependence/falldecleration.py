from django.db import models
from invoices.db.fields import CurrentUserField
from enums.falldecleration_enum import FallCircumstances, FallConsequences

from invoices.models import Patient
from constance import config

from invoices.employee import Employee

class FallDecleration(models.Model):
    class Meta:
        ordering = ['patient__id']
        verbose_name = u"Fall Decleration"
        verbose_name_plural = u"Fall Decleration"
    # Patient


    patient = models.ForeignKey(Patient,
                                help_text=u"Ne recheche que les patients pris en charge par l'assurance dépendance, vérifiez que la checkbox est validé si vous ne trouvez pas votre patient",
                                related_name='falldecleration_to_patient',
                                on_delete=models.CASCADE,
                                limit_choices_to={'is_under_dependence_insurance': True})
    datetimeOfFall = models.DateTimeField("Date, heure de la chute")
    placeOfFall = models.TextField("Lieu de la chute", max_length=200)

    declared_by = models.ForeignKey(Employee, verbose_name=u"Déclaré par",
                                     limit_choices_to=~models.Q(abbreviation__in=['XXX']),
                                     related_name='employee_of_means',
                                     on_delete=models.PROTECT,
                                     null=True, blank=True, default=None)
    witnesses = models.TextField(u"Témoins éventuels", max_length= 255,
                                null=True, blank=True, default=None)
    fall_circumstance = models.CharField(u"Circonstances de la chute", choices=FallCircumstances.choices, max_length= 255)
    other_fall_circumstance = models.CharField(u"Autre circonstances de la chute",  max_length= 255,
                                null=True, blank=True, default=None)
    incident_circumstance = models.TextField(u"Circonstances de l’incident", max_length= 255,
                                null=True, blank=True, default=None)
    other_fall_consequence = models.CharField(u"Autre conséquence de la chute",  max_length= 255,
                                null=True, blank=True, default=None)
    medications_risk_factor = models.TextField(u"Facteurs de risque", max_length= 255,
                                null=True, blank=True, default=None)
    cognitive_mood_diorders = models.TextField(u"Troubles cognitifs et/ou de l’humeur", max_length= 255,
                                null=True, blank=True, default=None)
    incontinence = models.TextField(u"Incontinence", max_length= 255,
                                null=True, blank=True, default=None)
    mobility_disability = models.TextField(u"Incapacité concernant les déplacements")
    unsuitable_footwear = models.BooleanField(u"Chaussures inadaptées", default=False)
    other_contributing_factor = models.TextField(u"Autre facteur favorisant", max_length= 255,
                                null=True, blank=True, default=None)
    preventable_fall = models.BooleanField(u"La chute aurait pu être prévenue")
    physician_informed = models.BooleanField(u"Le médecin a été avisé")
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)
    user = CurrentUserField(verbose_name='Créé par')


    @property
    def header_details(self):
        return [config.NURSE_NAME, config.MAIN_NURSE_CODE,
                config.NURSE_ADDRESS,
                config.NURSE_ZIP_CODE_CITY,
                config.NURSE_PHONE_NUMBER]

class FallConsequence(models.Model):
    fallDecleration = models.ForeignKey(FallDecleration, related_name='fall_consequences')
    consequence = models.CharField(choices=FallConsequences.choices, max_length=255)

class FallRequiredMedicalAct(models.Model):
    fallDecleration = models.ForeignKey(FallDecleration, related_name='fall_required_medical_acts')
    required_medical_act = models.CharField()
