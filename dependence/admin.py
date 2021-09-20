from dependence.forms import TypeDescriptionGenericInlineFormset
from dependence.models import AssignedPhysician, ContactPerson, DependenceInsurance, OtherStakeholder, BiographyHabits, \
    PatientAnamnesis, ActivityHabits, SocialHabits, MonthlyParameters, TensionAndTemperatureParameters
from django.contrib import admin
from admin_object_actions.admin import ModelAdminObjectActionsMixin
from fieldsets_with_inlines import FieldsetsInlineMixin


class AssignedPhysicianInLine(admin.TabularInline):
    extra = 0
    model = AssignedPhysician
    fields = ('assigned_physician',)
    autocomplete_fields = ['assigned_physician']


class ContactPersonInLine(admin.TabularInline):
    extra = 0
    model = ContactPerson
    fields = ('priority', 'contact_name', 'contact_relationship', 'contact_private_phone_nbr',
              'contact_business_phone_nbr')


class DependenceInsuranceInLine(admin.TabularInline):
    extra = 0
    model = DependenceInsurance
    fields = ('evaluation_date', 'ack_receipt_date', 'decision_date', 'rate_granted')


class OtherStakeholdersInLine(admin.TabularInline):
    extra = 0
    model = OtherStakeholder
    fields = ('contact_name', 'contact_pro_spec', 'contact_private_phone_nbr', 'contact_business_phone_nbr',
              'contact_email')


class BiographyHabitsInLine(admin.TabularInline):
    extra = 0
    model = BiographyHabits
    fields = ('habit_type', 'habit_time', 'habit_ritual', 'habit_preferences')
    formset = TypeDescriptionGenericInlineFormset


class ActivityHabitsInLine(admin.TabularInline):
    extra = 0
    model = ActivityHabits
    fields = ('habit_type', 'habit_description')
    formset = TypeDescriptionGenericInlineFormset


class SocialHabitsInLine(admin.TabularInline):
    extra = 0
    model = SocialHabits
    fields = ('habit_type', 'habit_description')
    formset = TypeDescriptionGenericInlineFormset


class TensionAndTemperatureParametersInLine(admin.TabularInline):
    extra = 0
    model = TensionAndTemperatureParameters
    fields = ('params_date_time', 'systolic_blood_press', 'diastolic_blood_press', 'temperature', 'stools', 'weight',
              'general_remarks', 'user', 'created_on', 'updated_on')
    readonly_fields = ('user', 'created_on', 'updated_on')


@admin.register(MonthlyParameters)
class PatientParameters(admin.ModelAdmin):
    fields = ('patient', 'params_year', 'params_month', 'weight')
    inlines = [TensionAndTemperatureParametersInLine]
    autocomplete_fields = ['patient']


@admin.register(PatientAnamnesis)
class PatientAnamnesisAdmin(ModelAdminObjectActionsMixin, FieldsetsInlineMixin, admin.ModelAdmin):
    list_display = ('patient', 'display_object_actions_list',)
    autocomplete_fields = ['patient']

    object_actions = [
        {
            'slug': 'print',
            'verbose_name': 'Print',
            'form_method': 'GET',
            'view': 'print_view',
        },
        {
            'slug': 'cover',
            'verbose_name': 'Cover Page',
            'form_method': 'GET',
            'view': 'print_cover',
        },
    ]

    readonly_fields = ("created_on", "updated_on",
                       'display_object_actions_detail',
                       )

    fieldsets_with_inlines = [
        ('Patient', {
            'fields': ('patient', 'nationality', 'civil_status', 'spoken_languages', 'external_doc_link',
                       'created_on', 'updated_on', 'display_object_actions_detail')
        }),
        ('Habitation', {
            'fields': ('house_type', 'floor_number', 'ppl_circle', 'door_key', 'entry_door'),
        }),
        (None, {
            'fields': ('health_care_dossier_location', 'preferred_pharmacies', 'preferred_hospital',
                       'informal_caregiver', 'pathologies', 'medical_background', 'allergies'),
        }),
        ('Aides techniques', {
            'fields': ('electrical_bed', 'walking_frame', 'cane', 'aqualift', 'remote_alarm', 'other_technical_help'),
        }),
        (u'Prothèses', {
            'fields': ('dental_prosthesis', 'hearing_aid', 'glasses', 'other_prosthesis'),
        }),
        (u'Médicaments', {
            'fields': ('drugs_managed_by', 'drugs_prepared_by', 'drugs_distribution', 'drugs_ordering',
                       'pharmacy_visits'),
        }),
        (u'Mobilisation', {
            'fields': ('mobilization', 'mobilization_description'),
        }),
        (u"Soins d'hygiène", {
            'fields': ('hygiene_care_location', 'shower_days', 'hair_wash_days', 'bed_manager', 'bed_sheets_manager',
                       'laundry_manager', 'laundry_drop_location', 'new_laundry_location'),
        }),
        (u"Nutrition", {
            'fields': ('weight', 'size', 'nutrition_autonomy', 'diet', 'meal_on_wheels', 'shopping_management',
                       'shopping_management_desc',),
        }),
        (u"Elimination", {
            'fields': ('urinary_incontinence', 'faecal_incontinence', 'protection', 'day_protection',
                       'night_protection', 'protection_ordered', 'urinary_catheter', 'crystofix_catheter',
                       'elimination_addnl_details'),
        }),
        (u"Garde/ Course sortie / Foyer", {
            'fields': ('day_care_center', 'day_care_center_activities', 'household_chores',),
        }),
        (u"Biographie", {
            'fields': ['preferred_drinks']
        }),
        BiographyHabitsInLine,
        ActivityHabitsInLine,
        # (u"Activités", {
        #     'fields': ['shower_habits', 'dressing_habits', 'occupation_habits', 'general_wishes']
        # }),
        SocialHabitsInLine,
        # (u"Social", {
        #     'fields': ['family_ties', 'friend_ties', 'important_persons_ties', ]
        # }),
        (u"Important", {
            'fields': ['bio_highlights', ]
        }),
        AssignedPhysicianInLine,
        ContactPersonInLine,
        OtherStakeholdersInLine,
        DependenceInsuranceInLine
    ]

    # fieldsets = (
    #     ('Patient', {
    #         'fields': ('patient', 'biography', 'nationality', 'civil_status', 'spoken_languages', 'external_doc_link',
    #                    'display_object_actions_detail')
    #     }),
    #     ('Habitation', {
    #         'fields': ('house_type', 'floor_number', 'ppl_circle', 'door_key', 'entry_door'),
    #     }),
    #     (None, {
    #         'fields': ('health_care_dossier_location', 'preferred_pharmacies', 'preferred_hospital',
    #                    'informal_caregiver', 'pathologies', 'medical_background', 'allergies'),
    #     }),
    #     ('Aides techniques', {
    #         'fields': ('electrical_bed', 'walking_frame', 'cane', 'aqualift', 'remote_alarm', 'other_technical_help'),
    #     }),
    #     (u'Prothèses', {
    #         'fields': ('dental_prosthesis', 'hearing_aid', 'glasses', 'other_prosthesis'),
    #     }),
    #     (u'Médicaments', {
    #         'fields': ('drugs_managed_by', 'drugs_prepared_by', 'drugs_distribution', 'drugs_ordering',
    #                    'pharmacy_visits'),
    #     }),
    #     (u'Mobilisation', {
    #         'fields': ('mobilization', 'mobilization_description'),
    #     }),
    #     (u"Soins d'hygiène", {
    #         'fields': ('hygiene_care_location', 'shower_days', 'hair_wash_days', 'bed_manager', 'bed_sheets_manager',
    #                    'laundry_manager', 'laundry_drop_location', 'new_laundry_location'),
    #     }),
    #     (u"Nutrition", {
    #         'fields': ('weight', 'size', 'nutrition_autonomy', 'diet', 'meal_on_wheels', 'shopping_management',
    #                    'shopping_management_desc',),
    #     }),
    #     (u"Elimination", {
    #         'fields': ('urinary_incontinence', 'faecal_incontinence', 'protection', 'day_protection',
    #                    'night_protection', 'protection_ordered', 'urinary_catheter', 'crystofix_catheter',
    #                    'elimination_addnl_details'),
    #     }),
    #     (u"Garde/ Course sortie / Foyer", {
    #         'fields': ('day_care_center', 'day_care_center_activities', 'household_chores',),
    #     }),
    # )

    # inlines = [BiographyHabitsInLine, AssignedPhysicianInLine, ContactPersonInLine, OtherStakeholdersInLine,
    #            DependenceInsuranceInLine]

    def print_view(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'patientanamnesis/print_anamnesis2.html', {'obj': obj})

    def print_cover(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'patientanamnesis/print_cover.html', {'obj': obj})
