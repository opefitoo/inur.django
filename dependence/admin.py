from datetime import timezone
import io

from admin_object_actions.admin import ModelAdminObjectActionsMixin
from django.contrib import admin
from django.http import HttpResponse
# report lab library
from django.utils.translation import gettext as _
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from constance import config 
from dependence.enums import falldeclaration_enum
from datetime import datetime
from reportlab.lib.units import mm, inch
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Table ,TableStyle,Paragraph
from textwrap import wrap
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import numpy as np
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER



from django.contrib.admin import SimpleListFilter
from django.core.checks import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, ManyToManyField
from django.forms import ModelMultipleChoiceField, CheckboxSelectMultiple
from django.urls import reverse
from django.utils.safestring import mark_safe
from fieldsets_with_inlines import FieldsetsInlineMixin
from dependence.careplan_pdf import generate_pdf


from dependence.aai import AAITransmission, AAITransDetail
from dependence.careplan import CarePlanDetail, CarePlanMaster, CareOccurrence
from dependence.cnscommunications import ChangeDeclarationFile, DeclarationDetail
from dependence.detailedcareplan import MedicalCareSummaryPerPatient, MedicalCareSummaryPerPatientDetail, \
    SharedMedicalCareSummaryPerPatientDetail
from dependence.falldeclaration import FallDeclaration
from dependence.forms import FallDeclarationForm, TypeDescriptionGenericInlineFormset, \
    TensionAndTemperatureParametersFormset
from dependence.longtermcareitem import LongTermCareItem
from dependence.medicalcaresummary import MedicalCareSummary
from dependence.models import AssignedPhysician, ContactPerson, DependenceInsurance, OtherStakeholder, BiographyHabits, \
    PatientAnamnesis, ActivityHabits, SocialHabits, MonthlyParameters, TensionAndTemperatureParameters
from invoices.employee import JobPosition
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
    list_display = ('patient', 'date_of_request', 'referent', 'date_of_evaluation', 'date_of_notification',
                    'plan_number', 'decision_number', 'level_of_needs', 'start_of_support', 'end_of_support',)
    # all fields are readonly
    readonly_fields = ('created_on', 'updated_on', 'patient', 'date_of_request', 'referent', 'date_of_evaluation',
                       'date_of_notification', 'plan_number', 'decision_number', 'level_of_needs', 'start_of_support',
                       'end_of_support', 'date_of_decision', 'special_package', 'nature_package', 'cash_package',
                       'fmi_right', 'sn_code_aidant', 'link_to_declaration_detail')

    def link_to_declaration_detail(self, instance):
        url = f'{reverse("admin:dependence_declarationdetail_changelist")}?patient__id={instance.patient.id}'
        return mark_safe('<a href="%s">%s</a>' % (url, "cliquez ici (%d)" % DeclarationDetail.objects.filter(
            patient_id=instance.patient.id).count()))

    link_to_declaration_detail.short_description = "Echanges client"
    #list_filter = (FilteringPatientsForMedicalCareSummaryPerPatient,)

@admin.register(MedicalCareSummary)
class MedicalCareSummaryAdmin(admin.ModelAdmin):
    readonly_fields = ('created_on', 'updated_on', 'parsing_date', 'count_of_supported_persons', 'date_of_submission')


@admin.register(DeclarationDetail)
class DeclarationDetailAdmin(admin.ModelAdmin):
    list_display = ('patient', 'year_of_count', 'month_of_count', 'change_type', 'change_reference', 'change_date')
    # all fields are readonly
    readonly_fields = ('patient', 'year_of_count', 'month_of_count', 'change_type', 'change_reference', 'change_date',
                       'change_organism_identifier','change_anomaly', 'information',)
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


def get_fall_mobility_disability(mobility_disability):
    choices = falldeclaration_enum.FallmMbilityDisability.choices
    for choice in choices :
        if mobility_disability == choice[0]:
            return _(choice[1])
    return ""

def get_medications_risk_factor_display(medications_risk_factor):
    
    
    choices=falldeclaration_enum.FallMedicationsRiskFactors.choices
    for choice in choices :
        if medications_risk_factor == choice[0]:
            return _(choice[1])
    return ""


def get_fall_circumstance_display(fall_circumstance_d):
    choices=falldeclaration_enum.FallCircumstances.choices
    for choice in choices :
        if fall_circumstance_d == choice[0]:
            return _(choice[1])
    return ""

def get_fall_consequence_display(fall_consequence_as_str):
    a_fall_consequence = falldeclaration_enum.FallConsequences(fall_consequence_as_str)
    if a_fall_consequence:
        return dict(falldeclaration_enum.FallConsequences.choices)[a_fall_consequence]
    return ''


def get_fall_cognitive_mood_diorders_display(fall_cognitive_mood_diorders_as_str):
    a_fall_cognitive_mood_diordersequence = falldeclaration_enum.FallCognitiveMoodDiorders(fall_cognitive_mood_diorders_as_str)
    if a_fall_cognitive_mood_diordersequence:
        return dict(falldeclaration_enum.FallCognitiveMoodDiorders.choices)[a_fall_cognitive_mood_diordersequence]
    return ''

def get_fall_required_medical_acts_display(fall_required_medical_acts_as_str):
    a_fall_required_medical_acts = falldeclaration_enum.FallRequiredMedicalActs(fall_required_medical_acts_as_str)
    if a_fall_required_medical_acts:
        return dict(falldeclaration_enum.FallRequiredMedicalActs.choices)[a_fall_required_medical_acts]
    return ''

def get_fall_incontinences_display(fall_incontinences_as_str):
    a_fall_incontinences = falldeclaration_enum.FallIncontinences(fall_incontinences_as_str)
    if a_fall_incontinences:
        return dict(falldeclaration_enum.FallIncontinences.choices)[a_fall_incontinences]
    return ''

def generate_pdf(objects):
        # Create a new PDF object
        # Create the HttpResponse object with the appropriate PDF headers.
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="report.pdf"'
                
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer)
        
        # Create the PDF object, using the response object as its "file.        
        p= canvas.Canvas(response)
        for fall_declaration in objects:
                
            #################        HEADER        ##########################
            #################     LOGO  + text below ########################   
            # set the position and size of the logo
            logo_x = 20
            logo_y = 770
            logo_width = 60
            logo_height = 60
            # read the image file and draw it on the PDF canvas
            logo_path = "invoices/static/patientanamnesis/images/xyz.png"
            logo_img = ImageReader(logo_path)
            p.drawImage(logo_img, logo_x, logo_y, width=logo_width, height=logo_height)
            # add some text below the logo
            p.setFont("Helvetica-Bold", 10)
            
            nurse_name = config.NURSE_NAME
            nurse_code = config.MAIN_NURSE_CODE
            nurse_phone_number = config.NURSE_PHONE_NUMBER
            nurse_address = config.NURSE_ADDRESS
            nurse_zip_code_city = config.NURSE_ZIP_CODE_CITY
            
            patient_gender = fall_declaration.patient.gender
            patient_first_name =fall_declaration.patient.first_name
            patient_name =fall_declaration.patient.name
            patient_code_sn = fall_declaration.patient.code_sn
            patient_address = fall_declaration.patient.address
            patient_zipcode = fall_declaration.patient.zipcode
            patient_clean_phone_number = fall_declaration.patient.phone_number
            
            
            p.drawString(logo_x,  logo_y - 15, f"{nurse_name} - ")
            p.drawString(logo_x + 100,  logo_y - 15, f"{nurse_code}")
            p.drawString(logo_x,  logo_y - 30, f"{nurse_address} - ")
            p.drawString(logo_x + 90,  logo_y - 30, f"{nurse_zip_code_city}")
            p.drawString(logo_x,  logo_y - 45, f"{nurse_phone_number}")
            
            
            if patient_gender == 'MAL': 
                p.drawString(logo_x + 400 ,  logo_y , f" Monsieur {patient_name} {patient_first_name}")
            elif patient_gender == 'FEM':
                p.drawString(logo_x + 400 ,  logo_y, f" Madame {patient_name} {patient_first_name}")
            else:
                p.drawString(logo_x + 400 ,  logo_y, f"{patient_name} {patient_first_name}")
            
            p.drawString(logo_x + 400 ,  logo_y - 10, f"{patient_address}")
            p.drawString(logo_x + 400 ,  logo_y - 20, f"{patient_zipcode}")
            p.drawString(logo_x + 400 ,  logo_y - 30, f"Tél.:  {patient_clean_phone_number}")
            
            #############################   End  HEADER #################################### 
            #############################   Content PDF ####################################
            
            # Help •••••••••••••••••••••••••••••••••••••••••••••••••••••••
            def drawMyRuler(pdf):
                    pdf.drawString(100,810, 'x100')
                    pdf.drawString(200,810, 'x200')
                    pdf.drawString(300,810, 'x300')
                    pdf.drawString(400,810, 'x400')
                    pdf.drawString(500,810, 'x500')

                    pdf.drawString(10,100, 'y100')
                    pdf.drawString(10,200, 'y200')
                    pdf.drawString(10,300, 'y300')
                    pdf.drawString(10,400, 'y400')
                    pdf.drawString(10,500, 'y500')
                    pdf.drawString(10,600, 'y600')
                    pdf.drawString(10,700, 'y700')
                    pdf.drawString(10,800, 'y800')  
            
            # drawMyRuler(p)
            
            # title
            
            # List of Lists
            data = [["Formulaire de constat de chute" ]]
            
            table= Table(data)
            
            
            p.setFont('Helvetica-Bold', 16)
            
            style = TableStyle([
                ('BACKGROUND', (0,0), (3,0), colors.white),
                ('TEXTCOLOR',(0,0),(-1,0),colors.black),

                ('ALIGN',(0,0),(-1,-1),'CENTER'),

                # ('FONTNAME', (0,0), (-1,0), 'Courier-Bold'),
                ('FONTNAME', (0,0), (-1,0), 'Times-Roman'),
                ('FONTSIZE', (0,0), (-1,0), 14),
                # ('BOTTOMPADDING', (0,0), (-1,0), 12),
                # ('BACKGROUND',(0,1),(-1,-1),colors.beige),
            ])
            table.setStyle(style)
            

            
            # Calculate the width and height of the table
            width, height = table.wrapOn(p, inch, inch)
            # Calculate the x and y coordinates to center the title on the canvas
            x = (8 * inch - width) / 2
            y = (19.5 * inch - height) / 2

            # Draw the table on the canvas
            table.drawOn(p, x, y)
            
            title_x = 298
            title_y = 670
            
            p.setFont('Helvetica-Bold', 9)
            p.drawString(50, title_y , "À remplir : après chaque chute.")
            
            # A •••••••••••••••••••••••••••••••••••••••••••••••••••••••
            
         
            A_y = title_y - 40 
            
            date_fall = fall_declaration.datetimeOfFall
            formatted_date_fall = datetime.strftime(date_fall, "%d %B %Y %H:%M")
            # p.drawString(30, A_y, f"A. Date, heure de la chute: {formatted_date_fall}")
            place_fall = fall_declaration.placeOfFall
            # p.drawString(380, A_y , f"Lieu de la chute:  {place_fall}") 
            
            declared_by_fall_f = fall_declaration.declared_by.user.first_name
            declared_by_fall_n = fall_declaration.declared_by.user.last_name
            
            # p.drawString(40, A_y - 15 , f"Déclaré par:{declared_by_fall_f} {declared_by_fall_n}")
            witness_fall = fall_declaration.witnesses
            
            def witnesses_value():
                if witness_fall :
                    return f"Témoins éventuels: {witness_fall}"
                else:
                    return "Aucun Témoins"
            #-----------------------------------------------------------------

            # List of Lists
            
            data = [[f"A. Date, heure de la chute: {formatted_date_fall}" , f"Lieu de la chute:  {place_fall}"],
                    [f"Déclaré par:{declared_by_fall_f} {declared_by_fall_n}" , witnesses_value() ],
            ]
            cell_width = 0.1*inch
            cell_height = 0.1*inch
            
            table= Table(data, colWidths=240, rowHeights=20) 
            
            p.setFont('Helvetica-Bold', 12)
                        
            # Add borders
            ts = TableStyle(
                [
                ('BACKGROUND', (0,0), (3,0), colors.green),
                ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
                # ('BOX',(0,0),(-1,-1),1,colors.black),
                # ('BOTTOMPADDING', (start_col, start_row), (end_col, end_row), padding)
                # ('LINEBEFORE',(2,1),(2,-1),2,colors.red),
                # ('LINEABOVE',(0,2),(-1,2),2,colors.green),
                ('GRID',(0,0),(-1,-1),1,colors.black),
                ('SIZE', (0,0), (-1,-1), cell_width, cell_height),
                ('FONTSIZE', (0,0), (-1,-1), 9),
                ]
            )
            table.setStyle(ts)
            
            # Calculate the width and height of the table
            width, height = table.wrapOn(p, inch, inch)
            # Calculate the x and y coordinates to center the title on the canvas
            x = (7.5 * inch - width) / 2
            y = (17.8 * inch - height) / 2
            
            # Draw the table on the canvas
            table.drawOn(p, x, y)
            
            # B •••••••••••••••••••••••••••••••••••••••••••••••••••••••
            
            B_y = title_y - 73
            
            fall_circumstance = fall_declaration.fall_circumstance
            fall_circumstance_d = get_fall_circumstance_display(fall_circumstance)
            ot_fall_circumstance = fall_declaration.other_fall_circumstance
            
            # p.drawString(30, B_y , "B. Circonstances de la chute")
            
            
            # Set up the text style
            text_style = p.beginText()
            text_style.setFont("Helvetica", 9)
            text_style.setFillColor("black")
            
            # create a text object
            textobject = p.beginText()
            textobject.setTextOrigin(50, B_y - 21)

            str_fall = "• " + str(fall_circumstance_d)
            wraped_text = "\n".join(wrap(str_fall, 30)) #
            
            # wrap the text into lines using the textLines() method
            lines = textobject.textLines(wraped_text)
            
            def fall_circumstance_value(): 
                if fall_circumstance != "FCI_OTHER_CAUSES" :
                    # p.drawString(50, B_y - 25 , f" • {textobject}")
                    # p.drawText(textobject)
                    return str_fall
                else:
                    return  f"   • {ot_fall_circumstance}"
                    # p.drawString(50, B_y - 22 , f" • {ot_fall_circumstance}")
            
            fall_incident_circumstance = fall_declaration.incident_circumstance
            
            # p.drawString(30, B_y- 49 , f"    Circonstances de l’incident:{fall_incident_circumstance}")
            
            
            #-----------------------------------------------------------------
            
            # List of Lists
            
            data = [["B. Circonstances de la chute"],
                    ["      "+ fall_circumstance_value()], 
                     [f"   Circonstances de l’incident:{fall_incident_circumstance}"],
            ]
            
            cell_width = 0.1*inch
            cell_height = 0.1*inch
            
            table= Table(data, colWidths=480, rowHeights=20) 
            
   
                        
            # Add borders
            ts = TableStyle(
                [
                ('BACKGROUND', (0,0), (3,0), colors.green),
                ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
                ('GRID',(0,0),(-1,-1),1,colors.black),
                ('SIZE', (0,0), (-1,-1), cell_width, cell_height),
                # ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9), 

                #merge the first row
                # ('SPAN', (0, 0), (1, 0)),  
                ]
            )
            table.setStyle(ts)
            # Calculate the width and height of the table
            width, height = table.wrapOn(p, inch, inch)
            # Calculate the x and y coordinates to center the title on the canvas
            x = (7.5 * inch - width) / 2
            y = (16.3 * inch - height) / 2
            
            # Draw the table on the canvas
            table.drawOn(p, x, y)
            
            # C ••••••••••••••••••••••••••••••••••••••••••••••••••••••••
            
            C_y = title_y - 140
            f_other_fall_consequence = fall_declaration.other_fall_consequence
            
            
            # print_consequence = dict(falldeclaration_enum.FallConsequences.choices)[falldeclaration_enum.FallConsequences(eval(fall_declaration.fall_consequences)[0])]
            # p.drawString(30, C_y , "C. Conséquences de la chute")
                        # Set up the styles for the table
            styles = getSampleStyleSheet()
            style_normal = styles['Normal']
            styleN = styles["BodyText"]
            styleN.alignment = TA_LEFT
            # List of Lists
            
            data = [["C. Conséquences de la chute","",""],
            ]
            con_X=30
            consequence_array=[]
            for consequence in  eval(fall_declaration.fall_consequences) :
                if consequence:
                    consequence_display = get_fall_consequence_display(fall_consequence_as_str=consequence)
                    # p.drawString(con_X, C_y - 28 , f"   • { _(consequence_display)}") 
                    consequence_cell = Paragraph(f"   • {_(consequence_display)}",styleN)
                    consequence_array.append(consequence_cell)
                    con_X+=130
            chunk_size = 3
            consequence_lines = 0
            while consequence_array:
                consequence_lines +=1
                chunk, consequence_array = consequence_array[:chunk_size], consequence_array[chunk_size:]                
                data.append(chunk)
            
            if f_other_fall_consequence:
                # p.drawString(50, C_y - 41 , f" •  {f_other_fall_consequence}")
                data.append([f" •  {f_other_fall_consequence}"])
            #-----------------------------------------------------------------
            cell_width = 0.1*inch
            cell_height = 0.1*inch
            table= Table(data, colWidths=[57*mm, 63*mm, 49*mm], rowHeights=None) 
            span_other_consequences = consequence_lines+1
            # Add borders
            ts = TableStyle(
                [
                ('BACKGROUND', (0,0), (3,0), colors.green),
                ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
                ('GRID',(0,0),(-1,-1),1,colors.black),
                ('SIZE', (0,0), (-1,-1), cell_width, cell_height),
                ('FONTSIZE', (0, 0), (-1, -1), 9), 
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                #merge the first row
                ('SPAN', (0, 0), (2, 0)), 
                # merge the third row
                ('SPAN', (0, span_other_consequences), (2, span_other_consequences)),   
                ]
            )
            
            table.setStyle(ts)
            
            # plus que 03 chopix en ajoute une ligne
            
            # Calculate the width and height of the table
            width, height = table.wrapOn(p, inch, inch)
            
            # Calculate the x and y coordinates to center the title on the canvas
            x = (7.5 * inch - width) / 2
            y = (14.2 * inch - height) / 2
            
            # Draw the table on the canvas
            table.drawOn(p, x, y)
            
            # D ••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
            
            
            
            
            D_y = title_y - 200  
            
            # List of Lists
            
            data = [["D. Actes médicaux et/ou infirmiers requis dans les 24h (plusieurs réponses possibles)","",""],
            ]
            
            fall_other_required_medical_act = fall_declaration.other_required_medical_act     
            # p.drawString(30,D_y , "D. Actes médicaux et/ou infirmiers requis dans les 24h (plusieurs réponses possibles)")
            
            medical_act_display_array =[]
            
            med_x=30
            for medical_act in  eval(fall_declaration.fall_required_medical_acts) :
                if medical_act:
                    medical_act_display = get_fall_required_medical_acts_display(fall_required_medical_acts_as_str=medical_act)
                    medical_act_cell = Paragraph(f"   • {_(medical_act_display)}",styleN)
                    medical_act_display_array.append(medical_act_cell)
                    # p.drawString(med_x, D_y - 28 , f"   • { _(medical_act_display)}") 
                    med_x+=130
            
            chunk_size = 3
            medical_act_lines = 0
            while medical_act_display_array:
                medical_act_lines +=1
                chunk, medical_act_display_array = medical_act_display_array[:chunk_size], medical_act_display_array[chunk_size:]                
                data.append(chunk)
            
            if fall_other_required_medical_act:
                # p.drawString(50, D_y - 41 , f" •  {fall_other_required_medical_act}")
                data.append([f" •  {fall_other_required_medical_act}"])
            
            
            
            #------------------------------------------------------------------
            
            
            cell_width = 0.1*inch
            cell_height = 0.1*inch
            table= Table(data, colWidths=[57*mm, 63*mm, 49*mm], rowHeights=None) 
            
            span_other_medical_act = medical_act_lines+1
            # Add borders
            ts = TableStyle(
                [
                ('BACKGROUND', (0,0), (3,0), colors.green),
                ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
                ('GRID',(0,0),(-1,-1),1,colors.black),
                ('SIZE', (0,0), (-1,-1), cell_width, cell_height),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'), 
                #merge the First row
                ('SPAN', (0, 0), (2, 0)), 
                # merge the third row
                ('SPAN', (0, span_other_medical_act), (2, span_other_medical_act)),   
            ]
            )
            table.setStyle(ts)
            
            # Calculate the width and height of the table
            width, height = table.wrapOn(p, inch, inch)
                        
            # Calculate the x and y coordinates to center the title on the canvas
            x = (7.5 * inch - width) / 2
            y = (11.8 * inch - height) / 2
            
            # Draw the table on the canvas
            table.drawOn(p, x, y)
            
            # E  •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
            
            # List of Lists
            
            dataE = [["E. Facteurs de risque","",""]]
            
            E_y = title_y - 260
            
            fall_medications_risk_factor =get_medications_risk_factor_display(fall_declaration.medications_risk_factor) 
            #----------------------------------------------------
            #****************************************************
            #1 --------------------------------------------------
            # p.drawString(30, E_y , "E. Facteurs de risque")
            
            if fall_medications_risk_factor:
                # p.drawString(50, E_y - 40 , f"  • {fall_medications_risk_factor}")
                dataE.append([f"  • {fall_medications_risk_factor}"])
            #----------------------------------------------------
            #****************************************************
            #2 ----------------------------------------------------
            # p.drawString(30, E_y - 15 , "   Troubles cognitifs et/ou de l’humeur")
            dataE.append(["   Troubles cognitifs et/ou de l’humeur"])
            
            trouble_array = []
            tro_x = 30
            for trouble in  eval(fall_declaration.fall_cognitive_mood_diorders) :
                if trouble:
                    trouble_display = get_fall_cognitive_mood_diorders_display(fall_cognitive_mood_diorders_as_str=trouble)
                    trouble_cell = Paragraph(f"   • {_(trouble_display)}",styleN)
                    trouble_array.append(trouble_cell)
                    # p.drawString(tro_x, E_y - 28 , f"   • { _(trouble_display)}") 
                    tro_x+=130
            
            chunk_size = 3
            trouble_lines = 2
            while trouble_array:
                trouble_lines +=1
                chunk, trouble_array = trouble_array[:chunk_size], trouble_array[chunk_size:]                
                dataE.append(chunk)
            
            #----------------------------------------------------
            #****************************************************
            #3 --------------------------------------------------
            
            # p.drawString(30, E_y - 60 , "   Incontinence")
            dataE.append(["   Incontinence"])
            incontinence_array = []
            inc_x = 30
            for incontinence in eval(fall_declaration.fall_incontinences) :
                if incontinence:
                    incontinence_display = get_fall_incontinences_display(fall_incontinences_as_str=incontinence)
                    incontinence_cell=Paragraph(f"  • { _(incontinence_display)}",styleN)
                    incontinence_array.append(incontinence_cell)
                    # p.drawString(inc_x, E_y - 70 , f"  • { _(incontinence_display)}") 
                    inc_x+=130
            
            dataE.append(incontinence_array)
            
            #----------------------------------------------------
            #****************************************************
            #4 --------------------------------------------------   
            # p.drawString(30, E_y  - 110 , "   Incapacité concernant les déplacements")
            dataE.append(["   Incapacité concernant les déplacements"])
            fall_mobility_disability= get_fall_mobility_disability(fall_declaration.mobility_disability)
            if fall_mobility_disability :
                # p.drawString(50, E_y  - 130 , f" • {fall_mobility_disability}")
                dataE.append([f" • {fall_mobility_disability}"])            
            
            #----------------------------------------------------
            #****************************************************
            #5 --------------------------------------------------
            fall_unsuitable_footwear= fall_declaration.unsuitable_footwear
            if fall_unsuitable_footwear:
                # p.drawString(30, E_y - 153 , "   Chaussures inadaptées: Oui")
                dataE.append(["   Chaussures inadaptées: Oui"])
            else:
                # p.drawString(30, E_y - 153 , "   Chaussures inadaptées: Non")             
                dataE.append(["   Chaussures inadaptées: Non"])            
            
            #----------------------------------------------------
            #****************************************************
            #6 --------------------------------------------------
            fall_other_contributing_factor = fall_declaration.other_contributing_factor
            
            if fall_other_contributing_factor :
                # p.drawString(30, E_y - 200 , f"   Autre facteur favorisant:{fall_other_contributing_factor}")
                dataE.append([f"   Autre facteur favorisant:{fall_other_contributing_factor}"])            
                        
            #------------------------------------------------------------------
            
            
            cell_width = 0.1*inch
            cell_height = 0.1*inch
            table= Table(dataE, colWidths=[57*mm, 63*mm, 49*mm], rowHeights=None) 
            span_other_trouble =trouble_lines + 1  # Incontinence 
            
            # Add borders
            ts = TableStyle(
                [
                ('BACKGROUND', (0,0), (3,0), colors.green),
                ('TEXTCOLOR',(0,0),(-1,0),colors.whitesmoke),
                ('GRID',(0,0),(-1,-1),1,colors.black),
                ('SIZE', (0,0), (-1,-1), cell_width, cell_height),
                ('FONTSIZE', (0, 0), (-1, -1), 9), 
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                #merge the First row
                ('SPAN', (0, 0), (2, 0)), #  E. Facteurs de risque
                ('SPAN', (0, 1), (2, 1)), # Médicaments
                ('SPAN', (0, 2), (2, 2)),  # Troubles cognitifs et/ou de l’humeur 
                # 3eme ligne • Agitation
                ('SPAN', (0, span_other_trouble), (2, span_other_trouble)),  # Incontinence 
                ('SPAN', (0, span_other_trouble +2), (2, span_other_trouble +2)),  # Incapacité concernant les déplacements
                ('SPAN', (0, span_other_trouble +3), (2, span_other_trouble +3)),  # se déplace seul avec difficulté avec ou sans moyens auxiliaire
                ('SPAN', (0, span_other_trouble +4), (2, span_other_trouble +4)),  # chaussures inadapté
                ('SPAN', (0, span_other_trouble +5), (2, span_other_trouble +5)),  # Autre facteur favorisant:
                
                
                # merge the fifth row
            ]
            )
            table.setStyle(ts)
            
            # Calculate the width and height of the table
            width, height = table.wrapOn(p, inch, inch)
                        
            # Calculate the x and y coordinates to center the title on the canvas
            x = (7.5 * inch - width) / 2
            y = (7.5 * inch - height) / 2
            
            # Draw the table on the canvas
            table.drawOn(p, x, y)
            
            
            
            # F •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
            
            dataFG = []
            
            F_y = title_y - 500
            fall_preventable_fall = fall_declaration.preventable_fall
            if fall_preventable_fall:
                # p.drawString(30, F_y , "F. La chute aurait pu être prévenue : Oui")
                dataFG.append(["F. La chute aurait pu être prévenue : Oui"])
            else:
                # p.drawString(30, F_y , "F. La chute aurait pu être prévenue : Non")
                dataFG.append(["F. La chute aurait pu être prévenue : Non"])
            
            
            # G •••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••••
            G_y =  title_y - 530
            fall_physician_informed = fall_declaration.physician_informed
            if fall_physician_informed :
                # p.drawString(30, G_y ,"G. Le médecin a été avisé :  Oui")
                dataFG.append(["G. Le médecin a été avisé :  Oui"])
            else:
                # p.drawString(30, G_y ,"G. Le médecin a été avisé :  Non")
                dataFG.append(["G. Le médecin a été avisé :  Non"])
            
            #------------------------------------------------------------------
            
            cell_width = 0.1*inch
            cell_height = 0.1*inch
            table= Table(dataFG,colWidths=480, rowHeights=20) 
            
            # Add borders
            ts = TableStyle(
                [
                ('BACKGROUND', (0,0), (-1,-1), colors.green),
                ('TEXTCOLOR',(0,0),(-1,-1),colors.whitesmoke),
                ('GRID',(0,0),(-1,-1),1,colors.black),
                ('SIZE', (0,0), (-1,-1), cell_width, cell_height),
                ('FONTSIZE', (0, 0), (-1, -1), 9), 
            ]
            )
            table.setStyle(ts)
            
            # Calculate the width and height of the table
            width, height = table.wrapOn(p, inch, inch)
                        
            # Calculate the x and y coordinates to center the title on the canvas
            x = (7.5 * inch - width) / 2
            y = (3.7 * inch - height) / 2
            
            # Draw the table on the canvas
            table.drawOn(p, x, y)
            
            # Close the PDF object cleanly, and we're done.
            # Pagination
            
            page_num = p.getPageNumber()
            text = "page %s" % page_num
            p.drawString(300, 20, text)
            
            # Move to the next page For other patient
            p.showPage()
        
        # Save the PDF
        p.save()
        
        # Get the value of the BytesIO buffer and write it to the response
        pdf = buffer.getvalue()
        buffer.close()
        response.write(pdf)
        return response


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
            'verbose_name': _('Print'),
            'form_method': 'GET',
            'view': 'print_fall_declaration',
        },
    ]
    
    def print_fall_declaration(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'falldeclaration/print_fall_declaration.html', {'obj': obj})
    
    ######################   create Django action for printing foc as PDF file
    
    actions = ['print_document']
    
    def print_document(self, request, queryset):
        response = generate_pdf(queryset)
        return response
    
    print_document.short_description = _("Print selected objects as PDF")
