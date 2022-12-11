from admin_object_actions.admin import ModelAdminObjectActionsMixin
from dependence.enums.falldecleration_enum import FallCircumstances
from dependence.falldecleration import FallCognitiveMoodDiorder, FallConsequence, FallDecleration, FallIncontinence, FallRequiredMedicalAct
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.core.checks import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, ManyToManyField
from django.forms import ModelMultipleChoiceField, CheckboxSelectMultiple
from fieldsets_with_inlines import FieldsetsInlineMixin

from dependence.aai import AAITransmission, AAITransDetail
from dependence.careplan import CarePlanDetail, CarePlanMaster, CareOccurrence
from dependence.careplan_pdf import generate_pdf
from dependence.forms import FallDeclerationForm, TypeDescriptionGenericInlineFormset, TensionAndTemperatureParametersFormset
from dependence.models import AssignedPhysician, ContactPerson, DependenceInsurance, OtherStakeholder, BiographyHabits, \
    PatientAnamnesis, ActivityHabits, SocialHabits, MonthlyParameters, TensionAndTemperatureParameters
from invoices.employee import JobPosition
from invoices.models import Patient


@admin.register(CareOccurrence)
class CareOccurrenceAdmin(admin.ModelAdmin):
    model = CareOccurrence


class CarePlanDetailInLine(admin.TabularInline):
    extra = 0
    model = CarePlanDetail
    params_occurrence = ModelMultipleChoiceField(widget=CheckboxSelectMultiple(), queryset=CareOccurrence.objects.all(),
                                                 required=True)
    required_skills = ModelMultipleChoiceField(widget=CheckboxSelectMultiple(), queryset=JobPosition.objects.all(),
                                               required=True, limit_choices_to={'is_involved_in_health_care': True})
    formfield_overrides = {
        ManyToManyField: {'widget': CheckboxSelectMultiple},
    }

    # fields = ('params_day_of_week',
    #           'time_start', 'time_end', 'care_actions')


class FilteringPatients(SimpleListFilter):
    title = 'Patient'
    parameter_name = 'patient'

    def lookups(self, request, model_admin):
        years = CarePlanMaster.objects.values('patient').annotate(dcount=Count('patient')).order_by()
        years_tuple = []
        for year in years:
            years_tuple.append(
                (year['patient'], "%s (%s)" % (Patient.objects.get(pk=year['patient']), str(year['dcount']))))
        return tuple(years_tuple)

    def queryset(self, request, queryset):
        value = self.value()
        if value is not None:
            return queryset.filter(patient__id=value)
        return queryset


class FilteringPatientsLinkedToParameters(SimpleListFilter):
    title = 'Patient'
    parameter_name = 'patient'

    def lookups(self, request, model_admin):
        years = MonthlyParameters.objects.values('patient').annotate(dcount=Count('patient')).order_by()
        years_tuple = []
        for year in years:
            years_tuple.append(
                (year['patient'], "%s (%s)" % (Patient.objects.get(pk=year['patient']), str(year['dcount']))))
        return tuple(years_tuple)

    def queryset(self, request, queryset):
        value = self.value()
        if value is not None:
            return queryset.filter(patient__id=value)
        return queryset


@admin.register(CarePlanMaster)
class CarePlanMasterAdmin(admin.ModelAdmin):
    list_display = ("patient", "plan_number", "plan_start_date", "last_valid_plan")
    list_filter = (FilteringPatients,)
    inlines = [CarePlanDetailInLine]
    autocomplete_fields = ['patient']

    def pdf_action(self, request, queryset):
        try:
            return generate_pdf(queryset)
        except ValidationError as ve:
            self.message_user(request, ve.message,
                              level=messages.ERROR)

    pdf_action.short_description = "Imprimer"

    actions = [pdf_action]
    readonly_fields = ('user', 'created_on', 'updated_on')


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
    formset = TensionAndTemperatureParametersFormset
    fields = ('params_date_time', 'systolic_blood_press', 'diastolic_blood_press', 'heart_pulse', 'temperature',
              'stools', 'oximeter_saturation', 'vas', 'weight', 'blood_glucose', 'general_remarks', 'user', 'created_on'
              , "updated_on")
    readonly_fields = ('user', 'created_on', 'updated_on')


@admin.register(MonthlyParameters)
class PatientParameters(ModelAdminObjectActionsMixin, admin.ModelAdmin):
    fields = ('patient', 'params_year', 'params_month', 'weight')
    list_filter = ('params_month', 'params_year', FilteringPatientsLinkedToParameters)
    list_display = ('patient', 'params_month', 'params_year', 'display_object_actions_list')
    inlines = [TensionAndTemperatureParametersInLine]
    autocomplete_fields = ['patient']

    object_actions = [
        {
            'slug': 'print_all_params',
            'verbose_name': 'Print ALL',
            'form_method': 'GET',
            'view': 'print_all_params',
        },
        {
            'slug': 'print_glucose_params',
            'verbose_name': 'F. Glycémie',
            'form_method': 'GET',
            'view': 'print_glucose_params',
        },

    ]

    def print_all_params(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'monthlyparameters/print_all_params.html', {'obj': obj})

    def print_glucose_params(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'monthlyparameters/print_glucose_params.html', {'obj': obj})


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


class AAITransDetailInLine(admin.TabularInline):
    extra = 0
    model = AAITransDetail


@admin.register(AAITransmission)
class AAITransmissionAdmin(ModelAdminObjectActionsMixin, admin.ModelAdmin):
    list_display = ('patient', 'transmission_number', 'display_object_actions_list',)
    autocomplete_fields = ['patient']
    readonly_fields = ('user', 'created_on', 'updated_on')
    inlines = [AAITransDetailInLine]

    object_actions = [
        {
            'slug': 'print_aai',
            'verbose_name': 'Imprimer',
            'form_method': 'GET',
            'view': 'print_aai',
        },
    ]

    def print_aai(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'aai/print_aai.html', {'obj': obj})

class FallConsequenceInLine(admin.StackedInline):
    
    extra = 0
    model = FallConsequence
    fields = ('consequence',)

    def has_add_permission(self, request, obj):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_view_permission(self, request, obj=None):
        return True

class FallRequiredMedicalAcInLine(admin.StackedInline):
    extra = 0
    model = FallRequiredMedicalAct
    fields = ('required_medical_act',)

    def has_add_permission(self, request, obj):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_view_permission(self, request, obj=None):
        return True

class FallCognitiveMoodDiorderInLine(admin.StackedInline):
    extra = 0
    model = FallCognitiveMoodDiorder
    fields = ('cognitive_mood_diorder',)

    def has_add_permission(self, request, obj):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_view_permission(self, request, obj=None):
        return True

class FallIncontinenceInLine(admin.StackedInline):
    extra = 0
    model = FallIncontinence
    fields = ('incontinence',)

    def has_add_permission(self, request, obj):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_view_permission(self, request, obj=None):
        return True


@admin.register(FallDecleration)
class FallDeclerationAdmin(ModelAdminObjectActionsMixin, admin.ModelAdmin):
    # fields = ('patient', 
    #               'datetimeOfFall',
    #               'placeOfFall',
    #               'declared_by',
    #               'witnesses',
    #               'fall_circumstance',
    #               'other_fall_circumstance',
    #               'incident_circumstance',
    #               'fall_consequences',
    #               'other_fall_consequence',
    #               'fall_required_medical_acts',
    #               'other_required_medical_act',
    #               'medications_risk_factor',
    #               'fall_cognitive_mood_diorders',
    #               'fall_incontinences',
    #               'mobility_disability',
    #               'unsuitable_footwear',
    #               'other_contributing_factor',
    #               'preventable_fall',
    #               'physician_informed',
    #     )
    form = FallDeclerationForm
    list_display = ('patient', 'datetimeOfFall', 'display_object_actions_list',)
    autocomplete_fields = ['patient']
    readonly_fields = ('user', 'created_on', 'updated_on')
    inlines = (FallConsequenceInLine,
               FallRequiredMedicalAcInLine,
               FallCognitiveMoodDiorderInLine,
               FallIncontinenceInLine
               )

    object_actions = [
        {
            'slug': 'print_fall_decleration',
            'verbose_name': 'Imprimer',
            'form_method': 'GET',
            'view': 'print_fall_decleration',
        },
    ]

    def print_fall_decleration(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'aai/print_fall_declaration.html', {'obj': obj})

