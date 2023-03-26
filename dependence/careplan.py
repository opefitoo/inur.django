from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from invoices.db.fields import CurrentUserField
from invoices.models import Patient


class CarePlanMaster(models.Model):
    class Meta:
        ordering = ['patient__id']
        verbose_name = u"Plan de Soins Détaillé"
        verbose_name_plural = u"Plans de Soins Détaillé"

    # Patient
    patient = models.ForeignKey(Patient,
                                help_text=u"Ne recheche que les patients pris en charge par l'assurance dépendance, vérifiez que la checkbox est validé si vous ne trouvez pas votre patient",
                                related_name='care_plan_to_patient',
                                on_delete=models.CASCADE,
                                limit_choices_to={'is_under_dependence_insurance': True})
    plan_number = models.PositiveSmallIntegerField("Num.")
    replace_plan_number = models.PositiveSmallIntegerField("Remplce Num.", blank=True, null=True)
    plan_start_date = models.DateField(u"À partir de:", help_text=u"Date du début d'application du plan des soins",
                                       default=timezone.now)
    plan_end_date = models.DateField(u"Jusqu'à:",
                                     help_text=u"Date de la fin d'application du plan des soins",
                                     null=True, blank=True, default=None)
    plan_decision_date = models.DateField(u"Date décision:", help_text=u"Date de la décision de l'assurance dépendance",
                                          blank=True, null=True)
    # field that links to MedicalCareSummaryPerPatient
    medical_care_summary_per_patient = models.ForeignKey('MedicalCareSummaryPerPatient',
                                                         help_text=u"Lien vers Résumé des soins médicaux par patient reçu de la CNS",
                                                         related_name='care_plan_to_medical_care_summary_per_patient',
                                                         on_delete=models.CASCADE, blank=True, null=True)

    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)
    user = CurrentUserField()
    # Logical fields
    last_valid_plan = models.BooleanField("Dernier plan valide", default=False)

    @property
    def display_plan_concordance(self):
        if self.medical_care_summary_per_patient:
            for plan in self.medical_care_summary_per_patient.medical_care_summary_per_patient_detail.all():
                if plan.plan_number == self.plan_number:
                    return plan.plan_concordance
        return "Concordance"

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
        result.update(CarePlanMaster.validate_only_one_valid_plan_per_patient(instance, data))
        result.update(CarePlanMaster.validate_plan_is_linked_to_patient(instance, data))
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

    @staticmethod
    def validate_only_one_valid_plan_per_patient(instance, data):
        messages = {}
        conflicts = CarePlanMaster.objects.filter(
            last_valid_plan=True). \
            filter(patient_id=data['patient_id']). \
            exclude(pk=instance.id)
        if conflicts.count() > 0:
            messages.update({'last_valid_plan':
                                 "il y a déjà au moins un plan valide dans le système %s" % conflicts[0]})
        return messages

    def validate_plan_is_linked_to_patient(self, data):
        messages = {}
        if self.medical_care_summary_per_patient is None:
            messages.update({'medical_care_summary_per_patient':
                                 "Le plan de soin doit être lié à un résumé des soins médicaux"})
        elif self.medical_care_summary_per_patient and self.patient != self.medical_care_summary_per_patient.patient:
            messages.update({'medical_care_summary_per_patient':
                                 "Le patient du plan de soin doit être le même que celui du résumé des soins médicaux"})
        return messages

    def __str__(self):
        return "Plan de %s - num. %s" % (self.patient, self.plan_number)


class CareOccurrence(models.Model):
    class Meta:
        ordering = ['value']
        verbose_name = u"Occurence des soins"
        verbose_name_plural = u"Occurences"

    str_name = models.CharField('Nom', max_length=50)
    value = models.CharField('Valeur', max_length=5, default="?")

    # validate that there is only one occurrence with the same value
    def clean(self):
        exclude = []
        super(CareOccurrence, self).clean_fields(exclude)
        messages = self.validate(self, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance, data):
        result = {}
        result.update(CareOccurrence.unique_care_occurrence_value(instance, data))
        return result

    @staticmethod
    def unique_care_occurrence_value(instance, data):
        messages = {}
        conflicts_count = CarePlanDetail.objects.filter(
            params_occurrence__value=data['value']). \
            exclude(pk=instance.id).count()
        if 0 < conflicts_count:
            messages.update({'value':
                                 "Il existe déjà un avec le numéro %s et ce patient dans le système" % data[
                                     'value']})
        return messages

    def __str__(self):
        return self.str_name


class CarePlanDetail(models.Model):
    class Meta:
        ordering = ['id']
        verbose_name = u"Détail"
        verbose_name_plural = u"Détails"

    name = models.CharField('Nom', max_length=50)
    params_occurrence = models.ManyToManyField(CareOccurrence,
                                               related_name="from_careplan_detail_to_occurence+",
                                               verbose_name="Occurence")

    time_start = models.TimeField("De")
    time_end = models.TimeField("A")
    long_term_care_items = models.ManyToManyField('LongTermCareItem',
                                                  related_name="care_plan_detail_to_long_term_care_item",
                                                  verbose_name="Prestations Assurance dépendance", blank=True,
                                                  )
    care_actions = models.TextField(u"Actions à prévoir", max_length=500)
    # Many to Many relation to LongTermCareItem

    care_plan_to_master = models.ForeignKey(CarePlanMaster, related_name="care_plan_detail_to_master",
                                            on_delete=models.CASCADE, null=True, blank=True, default=None)

    def calculate_count_per_week(self, care_item):
        if self.long_term_care_items.filter(pk=care_item.pk).exists():
            if self.params_occurrence.filter(value="*").exists():
                return 7
            else:
                return self.params_occurrence.count()
        else:
            return 0

    def clean(self):
        exclude = []
        super(CarePlanDetail, self).clean_fields(exclude)
        messages = self.validate(self, self.__dict__)
        #messages.update(self.validate_cannot_be_every_day_and_another_day_bis())
        #messages.update(self.validate_overlap())
        if messages:
            raise ValidationError(messages)
    def validate_cannot_be_every_day_and_another_day_bis(self):
        messages = {}
        if self.params_occurrence.count() > 1 and self.params_occurrence.filter(value="*").count() > 0:
            messages.update({'params_occurrence':
                                 "Vous ne pouvez pas avoir tous les jours et un autre jour"})
        return messages

    def validate_overlap(self):
        messages = {}
        if self.pk is None:
            overlaps = CarePlanDetail.objects.filter(
                parent=self.parent,
                time_start_lt=self.time_end,
                time_end__gt=self.time_start
            )
        else:
            overlaps = CarePlanDetail.objects.filter(
                care_plan_to_master=self.care_plan_to_master,
                time_start__lt=self.time_end,
                time_end__gt=self.time_start
            ).exclude(pk=self.pk)
        for overlap in overlaps:
            overlap_occurrences = set(overlap.params_occurrence.values_list('value', flat=True))
            current_occurrences = set(self.params_occurrence.values_list('value', flat=True))
            if overlap_occurrences == current_occurrences or "*" in overlap_occurrences or "*" in current_occurrences:
                messages.update({'time_start':
                                     "Il y a des chevauchements avec d'autres plans de soins %s" % overlap})
        return messages
    @staticmethod
    def validate(instance, data):
        messages = {}
        messages.update(CarePlanDetail.validate_time_start_before_time_end(data))
        #messages.update(CarePlanDetail.validate_cannot_be_every_day_and_another_day(instance, data))
        return messages
    @staticmethod
    def validate_time_start_before_time_end(data):
        messages = {}
        if data['time_start'] > data['time_end']:
            messages.update({'time_start':
                                 "L'heure de début doit être avant l'heure de fin"})
        return messages
    @staticmethod
    def validate_cannot_be_every_day_and_another_day(instance, data):
        messages = {}
        print(instance)
        if instance.params_occurrence.count() > 1 and instance.params_occurrence.filter(value="*").count() > 0:
            messages.update({'params_occurrence':
                                 "Vous ne pouvez pas sélectionner tous les jours et un autre jour"})
        return messages

    def days_of_week(self):
        # return as a list the value of the CareOccurrence object
        return [x.value for x in self.params_occurrence.all()]

    def __str__(self):
        # name et time start et end
        return "%s - %s - %s" % (self.name, self.time_start, self.time_end)
