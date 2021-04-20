from django.db import models
from django_countries.fields import CountryField

from invoices.enums.generic import CivilStatus, HouseType, RemoteAlarm, DentalProsthesis, HearingAid, DrugManagement, \
    MobilizationsType, NutritionAutonomyLevel, HabitType, DependenceInsuranceLevel
from invoices.models import Patient, Physician


class PatientAnamnesis(models.Model):
    class Meta:
        ordering = ['-id']
        verbose_name = u"Anamnèse Patient"
        verbose_name_plural = u"Anamnèses Patient"

    # Patient
    patient = models.ForeignKey(Patient, related_name='dep_anamnesis_to_patient',
                                on_delete=models.PROTECT)
    nationality = CountryField(u'Nationalité', blank_label='...', blank=True, null=True)
    spoken_languages = models.CharField(u'Langues parlées', max_length=40, default=None, blank=True, null=True)
    external_doc_link = models.URLField("URL doc. externe", default=None, blank=True, null=True)
    civil_status = models.CharField(u"État civil",
                                    max_length=7,
                                    choices=CivilStatus.choices,
                                    default=None,
                                    blank=True,
                                    null=True
                                    )
    # habitudes
    preferred_drinks = models.TextField("Boissons préfèrées", max_length=250, default=None, blank=True, null=True)
    shower_habits = models.TextField("Se soigner", help_text=u"douche, lavé, bain",
                                     max_length=100, default=None, blank=True, null=True)
    dressing_habits = models.TextField("Habillements", help_text="Goûts vestimentaires",
                                       max_length=100, default=None, blank=True, null=True)
    occupation_habits = models.TextField("Occupations", help_text="Profession, loisirs, sports, lecture, TV, musique, "
                                                                  "cinéma, sorties...",
                                         max_length=250, default=None, blank=True, null=True)
    general_wishes = models.TextField("Souhaits", max_length=250, default=None, blank=True, null=True)
    family_ties = models.TextField("Famille", max_length=200, default=None, blank=True, null=True)
    friend_ties = models.TextField("Amis", max_length=200, default=None, blank=True, null=True)
    important_persons_ties = models.TextField("Personnes importantes", max_length=200, default=None, blank=True, null=True)
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
    # p
    preferred_pharmacies = models.TextField("Pharmacie(s)", max_length=500, default=None, blank=True, null=True)
    preferred_hospital = models.CharField(u"Établissement hospitalier choisi", max_length=50, default=None, blank=True,
                                          null=True)
    health_care_dossier_location = models.CharField("Dossier de soins se trouve", max_length=50,
                                                    default=None,
                                                    blank=True,
                                                    null=True)
    informal_caregiver = models.CharField("Aidant informel", max_length=50, default=None, blank=True, null=True)
    pathologies = models.TextField("Pathologies", max_length=500, default=None, blank=True, null=True)
    medical_background = models.TextField(u"Antécédents", max_length=500, default=None, blank=True,
                                          null=True)
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
    # Mobilisation
    mobilization = models.CharField(u"Mobilisation", choices=MobilizationsType.choices, max_length=5, default=None,
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
    day_care_center_activities = models.CharField(u"Activités", max_length=50, default=None, blank=True, null=True)
    household_chores = models.BooleanField(u"Tâches domestiques", default=None, blank=True, null=True)

    @property
    def physicians_set(self):
        if self.id:
            return [p.assigned_physician for p in AssignedPhysician.objects.filter(anamnesis_id=self.id)]
        return None

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


class AssignedPhysician(models.Model):
    class Meta:
        verbose_name = u'Médecin Traitant'
        verbose_name_plural = u'Médecins Traitants'

    assigned_physician = models.ForeignKey(Physician, related_name='dep_assigned_physicians',
                                           help_text='Please enter physician of the patient',
                                           verbose_name=u"Médecin",
                                           on_delete=models.PROTECT, null=True, blank=True, default=None)
    anamnesis = models.ForeignKey(PatientAnamnesis, related_name='dep_patient_anamnesis',
                                  help_text='Please enter hospitalization dates of the patient',
                                  on_delete=models.PROTECT, null=True, blank=True, default=None)


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
                                          on_delete=models.PROTECT)
    priority = models.PositiveSmallIntegerField(u"Priorité",
                                                default=None,
                                                blank=True,
                                                null=True)
    contact_name = models.CharField("Nom", max_length=50)
    contact_relationship = models.CharField("Relation", max_length=20,
                                            default=None,
                                            blank=True,
                                            null=True)
    contact_private_phone_nbr = models.CharField(u"Tél. privé", max_length=30)
    contact_business_phone_nbr = models.CharField(u"Tél. bureau", max_length=30,
                                                  default=None,
                                                  blank=True,
                                                  null=True)
