import os
import uuid

from constance import config
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from dependence.models import AssignedPhysician, PatientAnamnesis, current_year, current_month
from invoices.db.fields import CurrentUserField
from invoices.employee import Employee
from invoices.enums.generic import MonthsNames
from invoices.models import Patient


def aai_objective_files(instance, filename):
    file_name, file_extension = os.path.splitext(filename)
    if instance.objective and instance.objective.patient:
        path = os.path.join("AAI", "%s_%s" % (str(instance.objective.patient), instance.objective.patient.id),
                            "objectives")
    else:
        path = os.path.join("AAI", "objectives")
    # add a short uuid to the filename to avoir confilct with same name files, should be unique
    short_uuid = uuid.uuid4().hex[:6]
    if instance.objective and instance.objective.patient:
        filename = "%s_%s_%s%s" % (file_name, short_uuid, instance.objective.patient.id, file_extension)
    else:
        filename = "%s_%s%s" % (file_name, short_uuid, file_extension)
    return os.path.join(path, filename)


class AAIObjective(models.Model):
    class Meta:
        ordering = ['objective']
        verbose_name = u"Objectif AAI"
        verbose_name_plural = u"Objectifs AAI"

    objective = models.CharField("Objectif", max_length=100)
    evaluation_date = models.DateField("Date d'évaluation")
    objective_reaching_date = models.DateField("Estimation date d'atteinte de l'objectif")
    description = models.TextField("Description détaillée", max_length=1000)
    patient = models.ForeignKey(Patient,
                                related_name='aai_objective_to_patient',
                                on_delete=models.CASCADE,
                                limit_choices_to={'is_under_dependence_insurance': True})
    status = models.CharField(_("statut"), max_length=15, choices=[
        ('pending', _("En attente")),
        ('in_progress', _("En cours")),
        ('completed', _("Complété")),
        ('archived', _("Archivé"))
    ], default='pending')
    # technical fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)

    def __str__(self):
        return self.objective


class AAIObjectiveFiles(models.Model):
    """
    Files or pictures that are related to an AAI objective
    """

    class Meta:
        verbose_name = _("Fichier lié à un objectif AAI")
        verbose_name_plural = _("Fichiers liés à un objectif AAI")

    objective = models.ForeignKey(AAIObjective, related_name="files", on_delete=models.CASCADE)
    file = models.FileField(_("Fichier"), upload_to=aai_objective_files)
    description = models.TextField(_("Description"), blank=True, null=True)

    def __str__(self):
        return self.file.name


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
    aai_year = models.PositiveIntegerField(
        default=current_year())

    aai_month = models.IntegerField(
        choices=MonthsNames.choices,
        default=current_month(),
    )
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

    @property
    def details_set(self):
        if self.id:
            return AAITransDetail.objects.filter(detail_to_aai_master_id=self.id).order_by(
                'date_time_means_set')
        return None

    @property
    def header_details(self):
        return [config.NURSE_NAME, config.MAIN_NURSE_CODE,
                config.NURSE_ADDRESS,
                config.NURSE_ZIP_CODE_CITY,
                config.NURSE_PHONE_NUMBER]

    @property
    def physicians_set(self):
        if self.id:
            anamnesis = PatientAnamnesis.objects.filter(patient__id=self.patient.id).first()
            if anamnesis:
                return [p.assigned_physician for p in AssignedPhysician.objects.filter(anamnesis_id=anamnesis.id)]
        return "N.D."

    def __str__(self):
        return "AAI de %s - num. %s" % (self.patient, self.transmission_number)


class AAITransDetail(models.Model):
    class Meta:
        ordering = ['date_time_means_set']
        verbose_name = u"Détail"
        verbose_name_plural = u"Détails"

    detail_to_aai_master = models.ForeignKey(AAITransmission,
                                             related_name="from_aai_detail_to_master",
                                             verbose_name="Détails", on_delete=models.PROTECT)
    # objectives = models.TextField("Objectifs", help_text="Prise en charge, lien avec AEV", max_length=100)
    # can link to multiple objectives
    link_to_objectives = models.ManyToManyField(AAIObjective, verbose_name="Lien avec objectifs")
    means = models.TextField("Moyens/Actions", max_length=500, null=True, blank=True, default=None)
    results = models.TextField(u"Résultats", max_length=600,
                               null=True, blank=True, default=None)
    session_duration = models.DurationField("Durée",
                                            help_text="Durée de la séance sous format HH:MM:SS",
                                            null=True, blank=True, default=None)
    transmission_picture = models.ImageField("Photo", upload_to="AAI/transmission_pictures",
                                            null=True, blank=True, default=None)
    date_time_means_set = models.DateTimeField("Date/h", null=True, blank=True, default=None)
    means_paraph = models.ForeignKey(Employee, verbose_name="Paraphe",
                                     # limit_choices_to={'abbreviation_is_not_xxx': True},
                                     limit_choices_to=models.Q(user__groups__name='ergo-kine'),
                                     related_name='employee_of_means',
                                     on_delete=models.PROTECT,
                                     null=True, blank=True, default=None)
