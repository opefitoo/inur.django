from django.core.exceptions import ValidationError
from django.db import models
from invoices.db.fields import CurrentUserField
from invoices.employee import Employee
from invoices.models import Patient


class AAITransmission(models.Model):
    class Meta:
        ordering = ['patient__id']
        verbose_name = u"Transmission AAI"
        verbose_name_plural = u"Transmissions AAI"

    # Patient
    patient = models.ForeignKey(Patient,
                                help_text=u"Ne recheche que les patients pris en charge par l'assurance dépendance, vérifiez que la checkbox est validé si vous ne trouvez pas votre patient",
                                related_name='aai_to_patient',
                                on_delete=models.CASCADE,
                                limit_choices_to={'is_under_dependence_insurance': True})
    transmission_number = models.PositiveSmallIntegerField("Numéro")
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)
    user = CurrentUserField(verbose_name='Créé par')

    def clean(self):
        exclude = []

        super(AAITransmission, self).clean_fields(exclude)
        messages = self.validate(self, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance, data):
        result = {}
        result.update(AAITransmission.unique_care_plan_number(instance, data))
        return result

    @staticmethod
    def unique_care_plan_number(instance, data):
        messages = {}
        conflicts_count = AAITransmission.objects.filter(
            transmission_number=data['transmission_number']). \
            filter(patient_id=data['patient_id']). \
            exclude(pk=instance.id).count()
        if 0 < conflicts_count:
            messages.update({'transmission_number':
                                 "Il existe déjà un avec le numéro %s et ce patient dans le système" % data[
                                     'transmission_number']})
        return messages

    def __str__(self):
        return "AAI de %s - num. %s" % (self.patient, self.transmission_number)


class AAITransDetail(models.Model):
    class Meta:
        ordering = ['id']
        verbose_name = u"Détail"
        verbose_name_plural = u"Détails"

    detail_to_aai_master = models.ForeignKey(AAITransmission,
                                             related_name="from_aai_detail_to_master",
                                             verbose_name="Détails", on_delete=models.PROTECT)
    objectives = models.TextField("Objectifs", help_text="Prise en charge, lien avec AEV", max_length=100)
    means = models.TextField("Moyens/Actions", max_length=100, null=True, blank=True, default=None)
    date_time_means_set = models.DateTimeField("Date/h", null=True, blank=True, default=None)
    means_paraph = models.ForeignKey(Employee, verbose_name="Paraphe",
                                     # limit_choices_to={'abbreviation_is_not_xxx': True},
                                     limit_choices_to=~models.Q(abbreviation__in=['XXX']),
                                     related_name='employee_of_means',
                                     on_delete=models.PROTECT,
                                     null=True, blank=True, default=None)

    results = models.TextField(u"Résultats", max_length=100,
                               null=True, blank=True, default=None)
    date_time_results_set = models.DateTimeField("Date/h", null=True, blank=True, default=None)
    results_paraph = models.ForeignKey(Employee, verbose_name="Paraphe",
                                       # limit_choices_to={'abbreviation_is_not_xxx': True},
                                       limit_choices_to=~models.Q(abbreviation__in=['XXX']),
                                       related_name='employee_of_results',
                                       on_delete=models.PROTECT,
                                       null=True, blank=True, default=None)
