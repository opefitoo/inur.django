from datetime import timezone

from admin_object_actions.admin import ModelAdminObjectActionsMixin
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.core.checks import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, ManyToManyField
from django.forms import ModelMultipleChoiceField, CheckboxSelectMultiple
from django.http import HttpResponse
from django.urls import reverse
from django.utils.safestring import mark_safe
from fieldsets_with_inlines import FieldsetsInlineMixin
from reportlab.pdfgen import canvas

from dependence.aai import AAITransmission, AAITransDetail
from dependence.careplan import CarePlanDetail, CarePlanMaster, CareOccurrence
from dependence.careplan_pdf import generate_pdf
from dependence.cnscommunications import ChangeDeclarationFile, DeclarationDetail
from dependence.detailedcareplan import MedicalCareSummaryPerPatient, MedicalCareSummaryPerPatientDetail, \
    SharedMedicalCareSummaryPerPatientDetail
from dependence.falldeclaration import FallDeclaration
from dependence.forms import FallDeclarationForm, TypeDescriptionGenericInlineFormset, \
    TensionAndTemperatureParametersFormset, CarePlanDetailForm
from dependence.longtermcareitem import LongTermCareItem
from dependence.medicalcaresummary import MedicalCareSummary
from dependence.models import AssignedPhysician, ContactPerson, DependenceInsurance, OtherStakeholder, BiographyHabits, \
    PatientAnamnesis, ActivityHabits, SocialHabits, MonthlyParameters, TensionAndTemperatureParameters
from dependence.pdf.basedata import basedata_view
from invoices.models import Patient


@admin.register(LongTermCareItem)
class LongTermCareItemAdmin(admin.ModelAdmin):
    list_display = ('code', 'description')


class SharedMedicalCareSummaryPerPatientDetailInline(admin.TabularInline):
    model = SharedMedicalCareSummaryPerPatientDetail
    extra = 0
    can_delete = False
    readonly_fields = ('item', 'medical_care_summary_per_patient', 'number_of_care', 'periodicity')


class MedicalCareSummaryPerPatientDetailInline(admin.TabularInline):
    model = MedicalCareSummaryPerPatientDetail
    extra = 0
    can_delete = False
    readonly_fields = ('item', 'medical_care_summary_per_patient', 'number_of_care', 'periodicity')


class FilteringPatientsForMedicalCareSummaryPerPatient(SimpleListFilter):
    title = 'Patient'
    parameter_name = 'patient'

    def lookups(self, request, model_admin):
        years = MedicalCareSummaryPerPatient.objects.values('patient').annotate(dcount=Count('patient')).order_by()
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


@admin.register(MedicalCareSummaryPerPatient)
class MedicalCareSummaryPerPatientAdmin(admin.ModelAdmin):
    inlines = [MedicalCareSummaryPerPatientDetailInline, SharedMedicalCareSummaryPerPatientDetailInline]
    list_display = ('patient', 'date_of_decision', 'date_of_notification_to_provider', 'level_of_needs', 'start_of_support', 'end_of_support','is_latest_plan')
    # all fields are readonly
    readonly_fields = ('created_on', 'updated_on', 'patient', 'date_of_request', 'referent', 'date_of_evaluation',
                       'date_of_notification', 'plan_number', 'decision_number', 'level_of_needs', 'start_of_support',
                       'end_of_support', 'date_of_decision', 'special_package', 'nature_package', 'cash_package',
                       'fmi_right', 'sn_code_aidant', 'link_to_declaration_detail','date_of_notification_to_provider')
    list_filter = (FilteringPatientsForMedicalCareSummaryPerPatient, 'date_of_decision')
    def is_latest_plan(self, obj):
        return obj.is_latest_plan
    is_latest_plan.boolean = True

    def link_to_declaration_detail(self, instance):
        url = f'{reverse("admin:dependence_declarationdetail_changelist")}?patient__id={instance.patient.id}'
        return mark_safe('<a href="%s">%s</a>' % (url, "cliquez ici (%d)" % DeclarationDetail.objects.filter(
            patient_id=instance.patient.id).count()))

    link_to_declaration_detail.short_description = "Echanges client"
    # list_filter = (FilteringPatientsForMedicalCareSummaryPerPatient,)


@admin.register(MedicalCareSummary)
class MedicalCareSummaryAdmin(admin.ModelAdmin):
    readonly_fields = ('created_on', 'updated_on', 'parsing_date', 'count_of_supported_persons', 'date_of_submission')


@admin.register(DeclarationDetail)
class DeclarationDetailAdmin(admin.ModelAdmin):
    list_display = ('patient', 'year_of_count', 'month_of_count', 'change_type', 'change_reference', 'change_date')
    # all fields are readonly
    readonly_fields = ('patient', 'year_of_count', 'month_of_count', 'change_type', 'change_reference', 'change_date',
                       'change_organism_identifier', 'change_anomaly', 'information',)
    # cannot delete
    can_delete = False

    # cannot add
    def has_add_permission(self, request):
        return False

    # cannot edit
    def has_change_permission(self, request, obj=None):
        return False

    # cannot delete and hide delete button
    def has_delete_permission(self, request, obj=None):
        return False


class DeclarationDetailInline(admin.StackedInline):
    model = DeclarationDetail
    extra = 0
    readonly_fields = ('change_anomaly',)


@admin.register(ChangeDeclarationFile)
class ChangeDeclarationFileAdmin(admin.ModelAdmin):
    inlines = [DeclarationDetailInline]
    list_display = (
        'provider_date_of_sending', 'internal_reference', 'generated_xml', 'generated_return_xml', 'created_on',
        'updated_on')
    list_filter = ('provider_date_of_sending',)
    readonly_fields = ('created_on', 'updated_on', 'generated_xml', 'sent_to_ftp_server', 'updates_log',)
    actions = ['send_xml_to_ftp']

    def send_xml_to_ftp(self, request, queryset):
        for obj in queryset:
            obj.send_xml_to_ftp()
            # datetime sent to the FTP server
            obj.sent_to_ftp_server = timezone.now()
            self.message_user(request, "XML sent to FTP")

    send_xml_to_ftp.short_description = "Send XML to FTP"

    #


@admin.register(CareOccurrence)
class CareOccurrenceAdmin(admin.ModelAdmin):
    model = CareOccurrence
    list_display = ('str_name', 'value')


class CarePlanDetailInLine(admin.TabularInline):
    extra = 0
    model = CarePlanDetail
    form = CarePlanDetailForm
    params_occurrence = ModelMultipleChoiceField(widget=CheckboxSelectMultiple(), queryset=CareOccurrence.objects.all(),
                                                 required=True)

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
        {
            'slug': 'generate_report',
            'verbose_name': 'Generate Report',
            'icon': 'fas fa-file-pdf',
            'form_method': 'GET',
            'view': 'generate_report',
        },
    ]

    readonly_fields = ("created_on", "updated_on",
                       'display_object_actions_detail',
                       )

    fieldsets_with_inlines = [
        ('Patient', {
            'fields': ('patient', 'nationality', 'civil_status', 'spoken_languages', 'external_doc_link',
                       'birth_place', 'contract_start_date', 'contract_end_date', 'contract_signed_date',
                       'contract_file',
                       'plan_of_share', 'help_for_cleaning', 'reason_for_dependence', 'anticipated_directives',
                       'anticipated_directives_doc_link',
                       'religious_beliefs',
                       'created_on', 'updated_on', 'display_object_actions_detail')
        }),
        ('Habitation', {
            'fields': ('house_type', 'floor_number', 'ppl_circle', 'door_key', 'entry_door', 'domestic_animals',
                       'elevator'),
        }),
        ('Informations médicales', {
            'fields': ('health_care_dossier_location', 'preferred_hospital',
                       'informal_caregiver', 'pathologies', 'medical_background', 'treatments', 'allergies'),
        }),
        ('Aides techniques', {
            'fields': ('electrical_bed', 'walking_frame', 'cane', 'aqualift', 'remote_alarm', 'technical_help',
                       'other_technical_help'),
        }),
        (u'Prothèses', {
            'fields': ('dental_prosthesis', 'hearing_aid', 'glasses', 'other_prosthesis'),
        }),
        (u'Médicaments', {
            'fields': ('drugs_managed_by', 'drugs_prepared_by', 'drugs_distribution', 'drugs_ordering',
                       'pharmacy_visits', 'preferred_pharmacies'),
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

    def generate_report(self, request, object_id, form_url='', extra_context=None, action=None):
        response = HttpResponse(content_type='application/pdf')
        obj = self.get_object(request, object_id)
        response['Content-Disposition'] = f'attachment; filename="{obj.patient.name}.pdf"'

        p = canvas.Canvas(response, pagesize=(792, 612))
        p.drawString(100, 100, f"Name: {obj.patient.name}")
        p.save()
        return basedata_view(request, obj)

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


@admin.register(FallDeclaration)
class FallDeclarationAdmin(ModelAdminObjectActionsMixin, admin.ModelAdmin):
    fields = ('patient',
              'datetimeOfFall',
              'placeOfFall',
              'declared_by',
              'file_upload',
              'witnesses',
              'fall_circumstance',
              'other_fall_circumstance',
              'incident_circumstance',
              'fall_consequences',
              'other_fall_consequence',
              'fall_required_medical_acts',
              'other_required_medical_act',
              'medications_risk_factor',
              'fall_cognitive_mood_diorders',
              'fall_incontinences',
              'mobility_disability',
              'unsuitable_footwear',
              'other_contributing_factor',
              'preventable_fall',
              'physician_informed',
              )
    form = FallDeclarationForm
    list_display = ('patient', 'datetimeOfFall', 'display_object_actions_list',)
    autocomplete_fields = ['patient']
    readonly_fields = ('user',
                       'created_on',
                       'updated_on',
                       )

    object_actions = [
        {
            'slug': 'print_fall_declaration',
            'verbose_name': 'Imprimer',
            'form_method': 'GET',
            'view': 'print_fall_declaration',
        },
    ]

    def print_fall_declaration(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'falldeclaration/print_fall_declaration.html', {'obj': obj})
