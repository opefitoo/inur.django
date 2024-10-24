from datetime import date, datetime

from constance import config
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django_countries.fields import CountryField

from dependence.detailedcareplan import MedicalCareSummaryPerPatient, SharedMedicalCareSummaryPerPatientDetail
from invoices.db.fields import CurrentUserField
from invoices.enums.generic import CivilStatus, HouseType, RemoteAlarm, DentalProsthesis, HearingAid, DrugManagement, \
    MobilizationsType, NutritionAutonomyLevel, HabitType, DependenceInsuranceLevel, ActivityType, SocialHabitType, \
    MonthsNames, VisualAnalogueScaleLvl, HelpForCleaning, LegalProtectionRegimes
from invoices.models import Patient, Physician, Bedsore


def current_year():
    return date.today().year


def current_month():
    return date.today().month


class MonthlyParameters(models.Model):
    class Meta:
        ordering = ['-id']
        verbose_name = u"Surveillance Paramètres"
        verbose_name_plural = u"Surveillances Param."

    params_year = models.PositiveIntegerField(
        default=current_year())

    params_month = models.IntegerField(
        choices=MonthsNames.choices,
        default=current_month(),
    )
    # Patient
    patient = models.ForeignKey(Patient, related_name='health_params_to_patient',
                                on_delete=models.PROTECT,
                                limit_choices_to=Q(is_under_dependence_insurance=True) | Q(
                                    is_eligible_to_parameter_surveillance=True))
    weight = models.DecimalField("Poids (KG)", max_digits=4, decimal_places=1)

    def clean(self):
        exclude = []

        super(MonthlyParameters, self).clean_fields(exclude)
        messages = self.validate(self, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance, data):
        result = {}
        result.update(MonthlyParameters.validate_one_per_year_month(instance, data))
        return result

    @staticmethod
    def validate_one_per_year_month(instance, data):
        messages = {}
        conflicts_count = MonthlyParameters.objects.filter(
            params_year=data['params_year']). \
            filter(params_month=data['params_month']). \
            filter(patient_id=data['patient_id']). \
            exclude(pk=instance.id).count()
        if 0 < conflicts_count:
            messages.update({'params_year':
                                 "Il existe déjà des paramètres pour le mois %s et ce patient dans le système" % data[
                                     'params_month']})
            messages.update({'params_month':
                                 "Il existe déjà des paramètres pour le mois %s et ce patient dans le système" % data[
                                     'params_month']})
            messages.update({'patient':
                                 "Il existe déjà des paramètres pour le mois %s et ce patient dans le système" % data[
                                     'params_month']})
        return messages

    def display_month(self):
        return MonthsNames(self.params_month).label

    @property
    def physicians_set(self):
        if self.id:
            anamnesis = PatientAnamnesis.objects.filter(patient__id=self.patient.id).first()
            if anamnesis:
                return [p.assigned_physician for p in AssignedPhysician.objects.filter(anamnesis_id=anamnesis.id)]
        return "N.D."

    @property
    def parameters_set(self):
        if self.id:
            return TensionAndTemperatureParameters.objects.filter(monthly_params_id=self.id).order_by(
                'params_date_time')
        return None

    @property
    def header_details(self):
        return [config.NURSE_NAME, config.MAIN_NURSE_CODE,
                config.NURSE_ADDRESS,
                config.NURSE_ZIP_CODE_CITY,
                config.NURSE_PHONE_NUMBER]

    def __str__(self):
        return "Paramètres de %s - %s/%s" % (self.patient, self.params_month, self.params_year)


class TensionAndTemperatureParameters(models.Model):
    class Meta:
        ordering = ['params_date_time']
        verbose_name = u"Paramètre"
        verbose_name_plural = u"Paramètres"

    params_date_time = models.DateTimeField("Date", default=datetime.now)
    systolic_blood_press = models.PositiveSmallIntegerField("Tension max.", default=0)
    diastolic_blood_press = models.PositiveSmallIntegerField("Tension min.", default=0)
    heart_pulse = models.PositiveSmallIntegerField("Pouls", default=None, blank=True, null=True)
    temperature = models.DecimalField("Température", max_digits=3, decimal_places=1, default=0, blank=True, null=True)
    stools_parameter = models.BooleanField("Selles",
                                           help_text="Veuillez cocher si les selles sont normales",
                                        default=False)
    vas = models.PositiveSmallIntegerField("EVA", choices=VisualAnalogueScaleLvl.choices, default=None, blank=True,
                                           null=True)
    weight = models.DecimalField("Poids (KG)", max_digits=4, decimal_places=1, default=None, blank=True, null=True)
    oximeter_saturation = models.PositiveSmallIntegerField("Saturation O2 %", default=None, blank=True, null=True)
    general_remarks = models.TextField("Remarques générales", max_length=200, default=None, blank=True, null=True)
    blood_glucose = models.DecimalField("Mesure de la glycémie", max_digits=4, decimal_places=1, default=None,
                                        blank=True,
                                        null=True)
    monthly_params = models.ForeignKey(MonthlyParameters, related_name='health_params_to_monthly_params',
                                       on_delete=models.CASCADE, default=None)
    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)
    user = CurrentUserField()

    def __str__(self):
        return "Tension min/max, Pouls, Température, Selles, SATU. O2, EVA, POIDS, GLYCÉMIE, REMARQUES de %s" % self.monthly_params


class PatientAnamnesis(models.Model):
    class Meta:
        ordering = ['-id']
        verbose_name = u"Anamnèse Patient"
        verbose_name_plural = u"Anamnèses Patient"

    # Technical Fields
    created_on = models.DateTimeField("Date création", auto_now_add=True)
    updated_on = models.DateTimeField("Dernière mise à jour", auto_now=True)
    # Patient
    patient = models.ForeignKey(Patient, related_name='dep_anamnesis_to_patient',
                                on_delete=models.PROTECT,
                                limit_choices_to={'is_under_dependence_insurance': True})
    nationality = CountryField(u'Nationalité', blank_label='...', blank=True, null=True)
    birth_place = models.CharField(u'Lieu de naissance', help_text="Ville/Pays", max_length=50, default=None,
                                   blank=True, null=True)
    contract_file = models.FileField(u"Contrat", upload_to='contracts/', default=None, blank=True, null=True)
    contract_signed_date = models.DateField(u"Date de signature du contrat", default=None, blank=True, null=True)
    contract_start_date = models.DateField(u"Date de début du contrat", default=None, blank=True, null=True)
    contract_end_date = models.DateField(u"Date de fin du contrat", default=None, blank=True, null=True)
    spoken_languages = models.CharField(u'Langues parlées', max_length=40, default=None, blank=True, null=True)
    legal_protection_regimes = models.CharField(u"Régimes de protection légale", max_length=50, default=None, blank=True,
                                               null=True,
                                                choices=LegalProtectionRegimes.choices)
    legal_protection_regimes_doc_link = models.FileField(u"Doc. régimes de protection légale",  #
                                                         upload_to='documents/legal_protection_regimes',
                                                         default=None,
                                                         blank=True,
                                                         null=True
                                                         )
    legal_protector_name_and_contact = models.CharField(u"Nom et contact du protecteur légal",
                                                        max_length=250,
                                                        default=None, blank=True, null=True)
    external_doc_link = models.URLField("URL doc. externe", default=None, blank=True, null=True)
    civil_status = models.CharField(u"État civil",
                                    max_length=7,
                                    choices=CivilStatus.choices,
                                    default=None,
                                    blank=True,
                                    null=True
                                    )
    # plan_of_share = models.CharField(u"Plan de partage",  #
    #                                  max_length=45,
    #                                  blank=True,
    #                                  null=True
    #                                  )
    help_for_cleaning = models.CharField(u"Aide pour le ménage",  #
                                         max_length=10,
                                         choices=HelpForCleaning.choices,
                                         default=None,
                                         blank=True,
                                         null=True
                                         )
    reason_for_dependence = models.TextField(u"Motif de prise en charge",  #
                                             max_length=150,
                                             blank=True,
                                             null=True
                                             )
    anticipated_directives = models.CharField(u"Directives anticipées",  #
                                              max_length=45,
                                              blank=True,
                                              null=True
                                              )
    anticipated_directives_doc_link = models.FileField(u"Doc. directives anticipées",  #
                                                       upload_to='documents/anticipated_directives',
                                                       default=None,
                                                       blank=True,
                                                       null=True
                                                       )
    religious_beliefs = models.CharField(u"Religion",  #
                                         max_length=45,
                                         blank=True,
                                         null=True
                                         )

    # habitudes
    preferred_drinks = models.TextField("Boissons préfèrées", max_length=250, default=None, blank=True, null=True)
    # shower_habits = models.TextField("Se soigner", help_text=u"douche, lavé, bain",
    #                                  max_length=100, default=None, blank=True, null=True)
    # dressing_habits = models.TextField("Habillements", help_text="Goûts vestimentaires",
    #                                    max_length=100, default=None, blank=True, null=True)
    # occupation_habits = models.TextField("Occupations", help_text="Profession, loisirs, sports, lecture, TV, musique, "
    #                                                               "cinéma, sorties...",
    #                                      max_length=250, default=None, blank=True, null=True)
    # general_wishes = models.TextField("Souhaits", max_length=250, default=None, blank=True, null=True)
    # family_ties = models.TextField("Famille", max_length=200, default=None, blank=True, null=True)
    # friend_ties = models.TextField("Amis", max_length=200, default=None, blank=True, null=True)
    # important_persons_ties = models.TextField("Personnes importantes", max_length=200, default=None, blank=True,
    #                                           null=True)
    bio_highlights = models.TextField("Important",
                                      help_text=u"Quelles sont les éléments marquants de votre vie, "
                                                "qui sont importants pour bien vous soigner ?", max_length=200,
                                      default=None, blank=True, null=True)

    # Habitation
    house_type = models.CharField("Type d'habitation",
                                  max_length=5,
                                  choices=HouseType.choices,
                                  default=None,
                                  blank=True,
                                  null=True
                                  )
    floor_number = models.PositiveSmallIntegerField(u"Étage",
                                                    default=None,
                                                    blank=True,
                                                    null=True)
    elevator = models.BooleanField(u"Ascenseur", default=None,  #
                                   blank=True,
                                   null=True)

    ppl_circle = models.CharField("Entourage",
                                  max_length=50,
                                  default=None,
                                  blank=True,
                                  null=True)

    door_key = models.BooleanField(u"Clé", default=None,
                                   blank=True,
                                   null=True)
    entry_door = models.CharField(u"Porte d'entrée", max_length=50,
                                  default=None,
                                  blank=True,
                                  null=True)
    domestic_animals = models.CharField(u"Animaux domestiques", max_length=50,  #
                                        default=None,
                                        blank=True,
                                        null=True)

    # p
    preferred_hospital = models.CharField(u"Établissement hospitalier choisi", max_length=50, default=None, blank=True,
                                          null=True)
    health_care_dossier_location = models.CharField("Dossier de soins se trouve", max_length=50,
                                                    default=None,
                                                    blank=True,
                                                    null=True)
    informal_caregiver = models.CharField("Aidant formel", max_length=50, default=None, blank=True, null=True)
    pathologies = models.TextField("Pathologies", max_length=500, default=None, blank=True, null=True)
    technical_help = models.TextField("Aides techniques", max_length=500, default=None, blank=True, null=True)  #

    medical_background = models.TextField(u"Antécédents", max_length=500, default=None, blank=True,
                                          null=True)
    treatments = models.TextField("Traitements", max_length=1000, default=None, blank=True, null=True)  #
    allergies = models.TextField("Allergies", max_length=250, default=None, blank=True, null=True)
    # aides techniques
    electrical_bed = models.BooleanField(u"Lit électrique", default=None, blank=True, null=True)
    walking_frame = models.BooleanField(u"Cadre de marche", default=None, blank=True, null=True)
    cane = models.BooleanField(u"Canne", default=None, blank=True, null=True)
    aqualift = models.BooleanField(u"Aqualift", default=None, blank=True, null=True)
    remote_alarm = models.CharField("Alarme", choices=RemoteAlarm.choices, default=None, blank=True, null=True,
                                    max_length=4)
    other_technical_help = models.CharField("Autres aides techniques", max_length=50, default=None, blank=True,
                                            null=True)
    # Protheses
    dental_prosthesis = models.CharField("Prothèses dentaires", choices=DentalProsthesis.choices, default=None,
                                         blank=True, null=True, max_length=5)
    hearing_aid = models.CharField("Appareil auditif", choices=HearingAid.choices, default=None, blank=True, null=True,
                                   max_length=4)
    glasses = models.BooleanField("Lunettes", default=None, blank=True, null=True)
    other_prosthesis = models.CharField("Autres", max_length=50, default=None, blank=True, null=True)
    # Médicaments
    drugs_managed_by = models.CharField("Prise en charge", choices=DrugManagement.choices, default=None, blank=True,
                                        null=True, max_length=5)
    drugs_prepared_by = models.CharField(u"Prépraration", max_length=30, default=None, blank=True, null=True)
    drugs_distribution = models.CharField("Distribution", max_length=30, default=None, blank=True, null=True)
    drugs_ordering = models.CharField(u"Commande des médicaments", max_length=30, default=None, blank=True, null=True)
    pharmacy_visits = models.CharField(u"Passages en pharmacie", max_length=30, default=None, blank=True, null=True)
    preferred_pharmacies = models.TextField("Pharmacie(s)", max_length=500, default=None, blank=True, null=True)  #

    # Mobilisation
    mobilization = models.CharField(u"Mobilisation", choices=MobilizationsType.choices,
                                    max_length=15, default=None,
                                    blank=True,
                                    null=True)
    mobilization_description = models.TextField("Description", max_length=250, default=None, blank=True,
                                                null=True)
    # Soins d'hygiène
    hygiene_care_location = models.CharField(u"Les soins se déroulent où?", max_length=50, default=None, blank=True,
                                             null=True)
    shower_days = models.CharField("Jours de douche", max_length=50, default=None, blank=True, null=True)
    hair_wash_days = models.CharField("Lavage cheveux", max_length=50, default=None, blank=True, null=True)
    bed_manager = models.CharField(u"Le lit est à faire par", choices=DrugManagement.choices, max_length=5,
                                   default=None,
                                   blank=True, null=True)
    bed_sheets_manager = models.CharField("Changement des draps", max_length=50, default=None, blank=True, null=True)
    laundry_manager = models.CharField("Linge est à faire par", choices=DrugManagement.choices, max_length=5,
                                       default=None, blank=True, null=True)

    laundry_drop_location = models.CharField(u"Le linge sale est à déposer où ?", max_length=50, default=None,
                                             blank=True, null=True)
    new_laundry_location = models.CharField(u"Les vêtements/serviettes etc. se trouvent où ?", max_length=50,
                                            default=None, blank=True, null=True)
    hygiene_general_remarks = models.TextField(u"Remarques générales", max_length=250, default=None, blank=True,
                                              null=True)
    # Nutrition
    weight = models.PositiveSmallIntegerField("Poids", default=None)
    size = models.PositiveSmallIntegerField("Taille en cm.", default=None)
    nutrition_autonomy = models.CharField("Sonde PEG", choices=NutritionAutonomyLevel.choices, max_length=5,
                                          default=None, blank=True, null=True)
    diet = models.CharField(u"Régime", max_length=50, default=None, blank=True, null=True)
    meal_on_wheels = models.BooleanField("Repas sur roues", default=None, blank=True, null=True)
    shopping_management = models.CharField(u"Commissions à faire par", choices=DrugManagement.choices, max_length=5,
                                           default=None, blank=True, null=True)
    shopping_management_desc = models.TextField(u"Description", max_length=250, default=None, blank=True, null=True)
    # Elimination
    urinary_incontinence = models.BooleanField("Incontinence urinaire", default=None, blank=True, null=True)
    faecal_incontinence = models.BooleanField(u"Incontinence fécale", default=None, blank=True, null=True)
    protection = models.BooleanField("Protection", default=None, blank=True, null=True)
    day_protection = models.CharField(u"Protection Pendant la journée", max_length=50, default=None, blank=True,
                                      null=True)
    night_protection = models.CharField(u"Protection Pendant la nuit", max_length=50, default=None, blank=True,
                                        null=True)
    protection_ordered = models.CharField(u"Protection à commander par", max_length=50, default=None, blank=True,
                                          null=True)
    urinary_catheter = models.BooleanField(u"Sonde urinaire", default=None, blank=True, null=True)
    crystofix_catheter = models.BooleanField(u"Crystofix", default=None, blank=True, null=True)
    elimination_addnl_details = models.TextField(u"Autres détails ou remarques", max_length=500, default=None,
                                                 blank=True, null=True)
    # Garde/ Course sortie / Foyer
    day_care_center = models.CharField(u"Foyer de jour", max_length=50, default=None, blank=True, null=True)
    day_care_center_activities = models.TextField(u"Activités", max_length=500, default=None, blank=True, null=True)
    household_chores = models.BooleanField(u"Tâches domestiques", default=None, blank=True, null=True)

    @property
    def physicians_set(self):
        if self.id:
            return [p.assigned_physician for p in AssignedPhysician.objects.filter(anamnesis_id=self.id)]
        return None

    def get_last_tension_and_temperature_parameters(self):
        if self.id:
            monthly_params = MonthlyParameters.objects.filter(patient_id=self.patient_id).first()
            if monthly_params:
                return TensionAndTemperatureParameters.objects.filter(monthly_params_id=monthly_params.id).order_by(
                    'params_date_time').last()
        return None

    @property
    def dependance_insurance_level(self):
        if self.id:
            care_summary_per_patient = MedicalCareSummaryPerPatient.objects.filter(patient_id=self.patient_id).all()
            if len(care_summary_per_patient) > 1:
                for c in care_summary_per_patient:
                    if c.is_latest_plan:
                        return c.level_of_needs
                raise Exception("More than one medical care summary per patient %s" % self.patient)
            elif len(care_summary_per_patient) == 1:
                return care_summary_per_patient[0].level_of_needs
            else:
                return "N.D."

    def get_list_of_beautiful_string_for_contact_persons(self):
        if self.id:
            # name (relation) - phone / phone2
            contact_persons = ContactPerson.objects.filter(patient_anamnesis_id=self.id).order_by('priority')
            return [
                " - ".join(
                    filter(None, [
                        f"{c.priority}" if c.priority is not None else None,
                        f"{c.contact_name}" if c.contact_name is not None else None,
                        f"({c.contact_relationship})" if c.contact_relationship is not None else None,
                        f"{c.contact_private_phone_nbr}" if c.contact_private_phone_nbr is not None else None,
                        f"{c.contact_business_phone_nbr}" if c.contact_business_phone_nbr is not None else None,
                        f"{c.contact_address}" if c.contact_address is not None else None
                    ])
                )
                for c in contact_persons
            ] or ["N.D."]

    def get_biography_habits(self):
        list_habits_strings = []
        if self.id:
            habits = BiographyHabits.objects.filter(biography_id=self.id).all()
            for habit in habits:
                list_habits_strings.append(
                    f"{habit.get_habit_type_display()} - {habit.habit_time} - {habit.habit_ritual} - {habit.habit_preferences}")
            return list_habits_strings

    def get_list_of_beautiful_string_for_main_assigned_physicians(self):
        if self.id:
            # name (relation) - phone / phone2
            assigned_physicians = AssignedPhysician.objects.filter(anamnesis_id=self.id).filter(main_attending_physician=True).all()
            if assigned_physicians:
                return [f"{c.assigned_physician.get_name_first_name_physician_speciality()} - {c.assigned_physician.phone_number}" for c in assigned_physicians]
        return None

    def get_list_of_beautiful_string_for_other_assigned_physicians(self):
        if self.id:
            # name (relation) - phone / phone2
            assigned_physicians = AssignedPhysician.objects.filter(anamnesis_id=self.id).filter(main_attending_physician=False).all()
            if assigned_physicians:
                return [f"{c.assigned_physician.get_name_first_name_physician_speciality()} - {c.assigned_physician.phone_number}" for c in assigned_physicians]
        return None

    @property
    def shared_care_plan(self):
        shared_care_plan_dict = {}
        if self.id:
            care_summary_per_patient = MedicalCareSummaryPerPatient.objects.filter(patient_id=self.patient_id).all()
            # if more than one throw an error
            if len(care_summary_per_patient) > 1:
                for c in care_summary_per_patient:
                    if c.is_latest_plan:
                        shared_care = SharedMedicalCareSummaryPerPatientDetail.objects.filter(
                            medical_care_summary_per_patient_id=c.id).all()
                        shared_plan = False
                        if len(shared_care) > 1:
                            shared_plan = True
                        shared_care_plan_dict['shared_plan'] = shared_plan
                        shared_care_plan_dict['sn_code_aidant'] = c.sn_code_aidant
                        return shared_care_plan_dict
                raise Exception("More than one medical care summary per patient %s" % self.patient)
            elif len(care_summary_per_patient) == 1:
                shared_care = SharedMedicalCareSummaryPerPatientDetail.objects.filter(
                    medical_care_summary_per_patient_id=care_summary_per_patient[0].id).all()
                shared_plan = False
                if len(shared_care) > 1:
                    shared_plan = True
                shared_care_plan_dict['shared_plan'] = shared_plan
                shared_care_plan_dict['sn_code_aidant'] = care_summary_per_patient[0].sn_code_aidant
                return shared_care_plan_dict
            else:
                shared_care_plan_dict['shared_plan'] = False
                shared_care_plan_dict['sn_code_aidant'] = None
                return shared_care_plan_dict

    def clean(self, *args, **kwargs):
        super(PatientAnamnesis, self).clean_fields()
        messages = self.validate(self.id, self.__dict__)
        if messages:
            raise ValidationError(messages)

    @staticmethod
    def validate(instance_id, data):
        result = {}
        # result.update(PatientAnamnesis.validate_only_one_type_for_inlines(instance_id, data))
        result.update(PatientAnamnesis.validate_patient_has_only_one_anamnesis(instance_id, data))
        return result

    @staticmethod
    def validate_only_one_type_for_inlines(instance_id, data):
        messages = {}
        if 'is_private' in data and not data['is_private']:
            code_sn = data['code_sn'].replace(" ", "")
            if Patient.objects.filter(code_sn=code_sn).exclude(pk=instance_id).count() > 0:
                messages = {'code_sn': 'Code SN must be unique'}
        return messages

    @staticmethod
    def validate_patient_has_only_one_anamnesis(instance_id, data):
        messages = {}
        if PatientAnamnesis.objects.filter(patient_id=data['patient_id']).count() > 1:
            messages = {
                'patient': 'Patient must have only one anamnesis another anamnesis already exists with id %s' % PatientAnamnesis.objects.filter(
                    patient_id=data['patient_id']).first().id}
        return messages

    def __str__(self):
        return "Anamanèse %s " % self.patient


class BiographyHabits(models.Model):
    class Meta:
        ordering = ['-id']
        verbose_name = u"Habitudes"
        verbose_name_plural = u"Habitudes"

    habit_type = models.CharField('Type',
                                  max_length=7,
                                  choices=HabitType.choices,
                                  default=None,
                                  blank=True,
                                  null=True
                                  )
    habit_time = models.TimeField("Heure")
    habit_ritual = models.CharField("Rite", max_length=50)
    habit_preferences = models.CharField(u"Préférences", max_length=50)
    biography = models.ForeignKey(PatientAnamnesis, related_name='dep_habit_patient_biography',
                                  help_text='Veuillez saisir les habitudes du bénéficiaire',
                                  on_delete=models.PROTECT, null=True, blank=True, default=None)

    def __str__(self):
        return self.habit_type


class ActivityHabits(models.Model):
    class Meta:
        ordering = ['-id']
        verbose_name = u"Habitude d'Activités"
        verbose_name_plural = u"Habitudes d'Activités"

    habit_type = models.CharField('Type',
                                  max_length=5,
                                  choices=ActivityType.choices,
                                  default=None,
                                  blank=True,
                                  null=True
                                  )
    habit_description = models.TextField("Description",
                                         help_text="Veuillez décrire les habitudes en fonction du type",
                                         max_length=200, default=None, blank=True, null=True)
    biography = models.ForeignKey(PatientAnamnesis, related_name='activity_habit_patient_biography',
                                  help_text='Veuillez saisir les habitudes du bénéficiaire',
                                  on_delete=models.PROTECT, null=True, blank=True, default=None)

    def __str__(self):
        return self.habit_type


class SocialHabits(models.Model):
    class Meta:
        ordering = ['-id']
        verbose_name = u"Habitude Sociale"
        verbose_name_plural = u"Habitudes Sociales"

    habit_type = models.CharField('Type',
                                  max_length=4,
                                  choices=SocialHabitType.choices,
                                  default=None,
                                  blank=True,
                                  null=True
                                  )
    habit_description = models.TextField("Description",
                                         help_text="Veuillez décrire les habitudes sociales",
                                         max_length=200, default=None, blank=True, null=True)
    biography = models.ForeignKey(PatientAnamnesis, related_name='social_habit_patient_biography',
                                  help_text='Veuillez saisir les habitudes du bénéficiaire',
                                  on_delete=models.PROTECT, null=True, blank=True, default=None)

    def __str__(self):
        return self.habit_type


class AssignedPhysician(models.Model):
    class Meta:
        verbose_name = u'Médecin Traitant'
        verbose_name_plural = u'Médecins Traitants'

    assigned_physician = models.ForeignKey(Physician, related_name='dep_assigned_physicians',
                                           help_text='Please enter physician of the patient',
                                           verbose_name=u"Médecin",
                                           on_delete=models.SET_NULL, null=True, blank=True, default=None)
    main_attending_physician = models.BooleanField(u"Traitant principal", default=False)
    anamnesis = models.ForeignKey(PatientAnamnesis, related_name='dep_patient_anamnesis',
                                  help_text='Please enter hospitalization dates of the patient',
                                  on_delete=models.SET_NULL, null=True, blank=True, default=None)


class DependenceInsurance(models.Model):
    class Meta:
        ordering = ['-id']
        verbose_name = "Décision Assurance dépendance"
        verbose_name_plural = "Décisions Assurance dépendance"

    dep_anamnesis = models.ForeignKey(PatientAnamnesis, related_name='dep_dep_ins_to_anamnesis',
                                      on_delete=models.PROTECT)
    evaluation_date = models.DateField(u"Date évaluation", default=None)
    ack_receipt_date = models.DateField(u"Accusè de réception", default=None, blank=True, null=True)
    decision_date = models.DateField(u"Date de la décision", default=None, blank=True, null=True)
    rate_granted = models.CharField(u"Forfait", choices=DependenceInsuranceLevel.choices, default=None, blank=True,
                                    null=True, max_length=3)


class OtherStakeholder(models.Model):
    class Meta:
        verbose_name = "Autre intervenant"
        verbose_name_plural = "Autres intervenants"

    stakeholder_anamnesis = models.ForeignKey(PatientAnamnesis, related_name='dep_stakeholder_to_anamnesis',
                                              on_delete=models.PROTECT)
    contact_name = models.CharField("Nom et prénom", max_length=50)
    contact_pro_spec = models.CharField(u"Spécialité", max_length=20,
                                        default=None,
                                        blank=True,
                                        null=True)
    contact_private_phone_nbr = models.CharField(u"Tél. privé", max_length=30)
    contact_business_phone_nbr = models.CharField(u"Tél. bureau", max_length=30,
                                                  default=None,
                                                  blank=True,
                                                  null=True)
    contact_email = models.EmailField(u"Email", max_length=30,
                                      default=None,
                                      blank=True,
                                      null=True)


class ContactPerson(models.Model):
    class Meta:
        verbose_name = "Personne de contact"
        verbose_name_plural = "Personnes de contact"

    patient_anamnesis = models.ForeignKey(PatientAnamnesis, related_name='dep_contactpers_to_anamnesis',
                                          on_delete=models.SET_NULL, null=True)
    priority = models.PositiveSmallIntegerField(u"Priorité",
                                                default=None,
                                                blank=True,
                                                null=True)
    contact_name = models.CharField("Nom", max_length=50)
    contact_address = models.CharField("Adresse", max_length=50,
                                       default=None,
                                       blank=True,
                                       null=True)
    contact_relationship = models.CharField("Relation", max_length=20,
                                            default=None,
                                            blank=True,
                                            null=True)
    contact_private_phone_nbr = models.CharField(u"Tél. privé", max_length=30)
    contact_business_phone_nbr = models.CharField(u"Tél. bureau", max_length=30,
                                                  default=None,
                                                  blank=True,
                                                  null=True)
