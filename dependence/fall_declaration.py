from django.db import models
from invoices.db.fields import CurrentUserField

from invoices.models import Patient
from constance import config

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
