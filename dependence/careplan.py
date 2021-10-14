
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from invoices.enums.generic import WeekDayNames
from invoices.models import Patient


class CarePlanMaster(models.Model):
    class Meta:
        ordering = ['patient__id']
        verbose_name = u"Plan de Soins Détaillé"
        verbose_name_plural = u"Plans de Soins Détaillé"

    # Patient
    patient = models.ForeignKey(Patient, related_name='care_plan_to_patient',
                                on_delete=models.CASCADE)
    plan_number = models.PositiveSmallIntegerField("Num.")
    replace_plan_number = models.PositiveSmallIntegerField("Remplce Num.", blank=True, null=True)
    plan_start_date = models.DateField(u"À partir de:", help_text=u"Date du début d'application du plan des soins",
                                       default=timezone.now)

    def clean(self):
        exclude = []

        super(CarePlanMaster, self).clean_fields(exclude)
        messages = self.validate(self, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance, data):
        result = {}
        result.update(CarePlanMaster.unique_care_plan_number(instance, data))
        result.update(CarePlanMaster.replace_plan_number_check(instance, data))
        return result

    @staticmethod
    def unique_care_plan_number(instance, data):
        messages = {}
        conflicts_count = CarePlanMaster.objects.filter(
            plan_number=data['plan_number']). \
            filter(patient_id=data['patient_id']). \
            exclude(pk=instance.id).count()
        if 0 < conflicts_count:
            messages.update({'plan_number':
                                 "Il existe déjà un avec le numéro %s et ce patient dans le système" % data[
                                     'plan_number']})
        return messages

    @staticmethod
    def replace_plan_number_check(instance, data):
        messages = {}
        if data['replace_plan_number'] is None:
            return messages
        conflicts_count = CarePlanMaster.objects.filter(
            plan_number=data['replace_plan_number']). \
            filter(patient_id=data['patient_id']). \
            exclude(pk=instance.id).count()
        if 0 == conflicts_count:
            messages.update({'replace_plan_number':
                                 "il n'y a pas de plan avec le numéro %s dans le système" % data[
                                     'replace_plan_number']})
        return messages

    def __str__(self):
        return "Plan de %s - num. %s" % (self.patient, self.plan_number)


class CarePlanDetail(models.Model):
    class Meta:
        ordering = ['id']
        verbose_name = u"Détail"
        verbose_name_plural = u"Détails"

    params_day_of_week = models.IntegerField("Jour",
                                             choices=WeekDayNames.choices
                                             )

    time_start = models.TimeField("De")
    time_end = models.TimeField("A")
    care_actions = models.TextField(u"Actions à prévoir", max_length=500)
    care_plan_to_master = models.ForeignKey(CarePlanMaster, related_name="care_plan_detail_to_master",
                                            on_delete=models.CASCADE, null=True, blank=True, default=None)
