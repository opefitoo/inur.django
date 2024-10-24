import csv

from admin_object_actions.admin import ModelAdminObjectActionsMixin
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.checks import messages
from django.core.exceptions import ValidationError
from django.db.models import Count, Q, Sum, F
from django.db.models.functions import ExtractMonth
from django.forms import ModelMultipleChoiceField
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
# report lab library
from django.utils.translation import gettext as _
from fieldsets_with_inlines import FieldsetsInlineMixin
from reportlab.pdfgen import canvas

from dependence.aai import AAITransmission, AAITransDetail, AAIObjective, AAIObjectiveFiles
from dependence.actions.activity import duplicate_for_next_month, export_selected_to_csv, \
    generate_activity_details_from_events
from dependence.actions.initial_data import create_or_update_long_term_item_based_on_fixture
from dependence.actions.monthly import create_assurance_dependance_invoices_sept_2024
from dependence.actions.transfertdoc import generate_transfer_document
from dependence.activity import LongTermMonthlyActivity, LongTermMonthlyActivityDetail, LongTermMonthlyActivityFile
from dependence.careplan import CarePlanDetail, CarePlanMaster, CareOccurrence
from dependence.careplan_pdf import generate_pdf
from dependence.cnscommunications import ChangeDeclarationFile, DeclarationDetail, InformalCaregiverUnavailability
from dependence.detailedcareplan import MedicalCareSummaryPerPatient, MedicalCareSummaryPerPatientDetail, \
    SharedMedicalCareSummaryPerPatientDetail
from dependence.falldeclaration import FallDeclaration, FallDeclarationReportPicture
from dependence.filters import SubContractorFilter
from dependence.forms import FallDeclarationForm, TypeDescriptionGenericInlineFormset, \
    TensionAndTemperatureParametersFormset, CarePlanDetailForm, LongTermMonthlyActivityFileAdminForm, \
    LongTermCareInvoiceLineInlineFormset
from dependence.invoicing import LongTermCareInvoiceFile, LongTermCareInvoiceLine, LongTermCareMonthlyStatement, \
    LongTermCareInvoiceItem, LongTermCareMonthlyStatementSending
from dependence.longtermcareitem import LongTermPackage, LongTermPackagePrice, LongTermCareItem
from dependence.medicalcaresummary import MedicalCareSummary
from dependence.models import AssignedPhysician, ContactPerson, DependenceInsurance, OtherStakeholder, BiographyHabits, \
    PatientAnamnesis, ActivityHabits, SocialHabits, MonthlyParameters, TensionAndTemperatureParameters
from dependence.pdf.basedata import basedata_view
from dependence.print_fall_declaration import generate_pdf_fall_declaration
from invoices.filters.anamnesis import DeceasedFilter, ClientLeftFilter
from invoices.models import Patient, MedicalPrescription, Bedsore, ClientPatientRelationship


class LongTermCareInvoiceLineInline(admin.TabularInline):
    model = LongTermCareInvoiceLine
    extra = 0
    formset = LongTermCareInvoiceLineInlineFormset


class LongTermCareInvoiceItemInLine(admin.TabularInline):
    model = LongTermCareInvoiceItem
    extra = 0

    # fields : all fields + copy
    fields = ('care_date', 'long_term_care_package', 'quantity', "paid","refused_by_insurance","comment",
              "xml_invoice_reference","subcontractor", 'copy')
    readonly_fields = ('copy', )

    class Media:
        js = ['admin/js/vendor/jquery/jquery.min.js',
            'admin/js/jquery.init.js',
              "js/aev-inline-copy.js"]

    def copy(self, obj):
        return format_html("<a href='#' class='copy_inline'>copy</a>")
    copy.allow_tags = True




@admin.register(LongTermCareInvoiceFile)
class LongTermCareInvoiceFileAdmin(ModelAdminObjectActionsMixin, admin.ModelAdmin):
    inlines = [LongTermCareInvoiceLineInline, LongTermCareInvoiceItemInLine]
    list_display = ('patient', 'invoice_start_period', 'invoice_end_period', 'invoice_reference', 'has_errors_col',
                    'display_object_actions_list', 'has_subcontractor', 'link_to_monthly_statement')
    list_filter = ('patient', 'invoice_start_period', 'invoice_end_period', 'link_to_monthly_statement',
                   SubContractorFilter)
    date_hierarchy = 'invoice_start_period'
    readonly_fields = ('has_errors_col', 'display_errors_as_html',
                       'invoice_reference', 'created_on', 'updated_on')
    actions = ['create_pdf_version', 'copy_prestations_in_error_to_new_invoice', 'link_invoice_to_LongTermCareMonthlyStatement']

    object_actions = [
        {
            'slug': 'print_long_term_invoice',
            'verbose_name': 'Print',
            'form_method': 'GET',
            'view': 'print_long_term_invoice',
        },
        {
            'slug': 'print_subcontracting_invoice',
            'verbose_name': 'Subcontracting',
            'form_method': 'GET',
            'view': 'print_subcontracting_invoice',
        },

    ]

    def link_invoice_to_LongTermCareMonthlyStatement(self, request, queryset):
        # test if super user
        if not request.user.is_superuser:
            self.message_user(request, "Only superuser can link to LongTermCareMonthlyStatement", level=messages.ERROR)
            return
        longTermCareMonthlyStatement_id = None
        for obj in queryset:
            longTermCareMonthlyStatement_id = obj.link_operation_invoice_to_monthly_statement(LongTermCareMonthlyStatement_id=longTermCareMonthlyStatement_id)

    def export_to_xero(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Only superuser can export to Xero", level=messages.ERROR)
            return
        for obj in queryset:
            obj.export_to_xero()

    def copy_prestations_in_error_to_new_invoice(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Only superuser can copy to new invoice", level=messages.ERROR)
            return
        invoices_copied = []
        for obj in queryset:
            invoices_copied = obj.copy_prestations_in_error_to_new_invoice()
        self.message_user(request, "Invoices copied %s" % invoices_copied)



    def has_errors_col(self, obj):
        return not obj.has_errors

    has_errors_col.short_description = 'No Errors'  # Column header
    has_errors_col.boolean = True

    def print_long_term_invoice(self, request, object_id, form_url='', extra_context=None, action=None):
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'invoicing/print_long_term_invoice.html', {'obj': obj})

    def print_subcontracting_invoice(self, request, object_id, form_url='', extra_context=None, action=None):
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'invoicing/print_subcontracting_invoice.html', {'obj': obj})


class LongTermCareMonthlyStatementSendingInline(admin.TabularInline):
    model = LongTermCareMonthlyStatementSending
    extra = 0


@admin.register(LongTermCareMonthlyStatement)
class LongTermCareMonthlyStatementAdmin(ModelAdminObjectActionsMixin, admin.ModelAdmin):
    list_display = ('year', 'month', 'date_of_submission', 'display_object_actions_list')
    readonly_fields = ('created_on', 'updated_on', 'display_longTermCareInvoiceFiles')
    inlines = [LongTermCareMonthlyStatementSendingInline]
    actions = ['merge_selected_invoices']

    object_actions = [
        {
            'slug': 'print_statement_invoice',
            'verbose_name': 'Print',
            'form_method': 'GET',
            'view': 'print_statement_invoice',
        },
        {
            'slug': 'print_detailed_statement_invoice',
            'verbose_name': 'Détails',
            'form_method': 'GET',
            'view': 'print_detailed_statement_invoice',
        },
        {
            'slug': 'print_statement_invoice_to_be_sent',
            'verbose_name': 'Mémoire à envoyer',
            'form_method': 'GET',
            'view': 'print_statement_invoice_to_be_sent',
        },

    ]

    def print_statement_invoice(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'invoicing/print_statement_invoice.html', {'obj': obj})

    def print_detailed_statement_invoice(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'invoicing/print_detailed_statement_invoice.html', {'obj': obj})

    def print_statement_invoice_to_be_sent(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'invoicing/print_statement_invoice_to_be_sent.html', {'obj': obj})

    def merge_selected_invoices(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Only superuser can merge invoices", level=messages.ERROR)
            return
        # all LongTermCareMonthlyStatement must be same year and month
        year = None
        month = None
        for obj in queryset:
            if year is None:
                year = obj.year
                month = obj.month
            if year != obj.year or month != obj.month:
                self.message_user(request, "All selected invoices must be from the same year and month",
                                  level=messages.ERROR)
                return
        # create a new invoice that will contain all the selected invoices
        new_invoice = LongTermCareMonthlyStatement.objects.create(year=year,
                                                                    month=month,
                                                                    date_of_submission=timezone.now(),
                                                                    description="Merged invoice %s" % queryset)
       # take all LongTermCareInvoiceFile and link them to the new invoice
        all_LongTermCareInvoiceFiles = LongTermCareInvoiceFile.objects.filter(link_to_monthly_statement__in=queryset)
        for invoice_file in all_LongTermCareInvoiceFiles:
            invoice_file.link_to_monthly_statement = new_invoice
            invoice_file.save()
        self.message_user(request, "LongTermCareInvoiceFile %s linked to new invoice %s" % (all_LongTermCareInvoiceFiles, new_invoice))


class LongTermPackagePriceInline(admin.TabularInline):
    extra = 0
    model = LongTermPackagePrice


@admin.register(LongTermCareItem)
class LongTermCareItemAdmin(admin.ModelAdmin):
    list_display = ('code', 'short_description')
    actions = [create_or_update_long_term_item_based_on_fixture]


@admin.register(LongTermPackage)
class LongTermPackageAdmin(admin.ModelAdmin):
    list_display = ('code', 'description', 'get_latest_price_and_date')
    inlines = [LongTermPackagePriceInline]
    actions = ['remove_duplicates']
    readonly_fields = ('get_latest_price_and_date',)

    def remove_duplicates(self, request, queryset):
        if not request.user.is_superuser:
            return
        for long_term_package in queryset:
            prices = LongTermPackagePrice.objects.filter(package=long_term_package).order_by('start_date', 'id')
            seen_dates = set()
            for price in prices:
                dup_message = ""
                if price.start_date in seen_dates:
                    dup_message += "dup: %s, " % price
                    price.delete()
                else:
                    seen_dates.add(price.start_date)
        self.message_user(request, "One of each set of duplicates removed successfully %s" % dup_message)

    remove_duplicates.short_description = 'Remove one of each set of duplicates'


class SharedMedicalCareSummaryPerPatientDetailInline(admin.TabularInline):
    model = SharedMedicalCareSummaryPerPatientDetail
    extra = 0
    can_delete = False
    readonly_fields = (
        'item', 'medical_care_summary_per_patient', 'custom_description', 'number_of_care', 'periodicity')


class MedicalCareSummaryPerPatientDetailInline(admin.TabularInline):
    model = MedicalCareSummaryPerPatientDetail
    extra = 0
    can_delete = False
    readonly_fields = ('item', 'medical_care_summary_per_patient', 'custom_description',
                       'number_of_care', 'periodicity')


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
    list_display = ('patient', 'date_of_decision', 'date_of_notification_to_provider', 'level_of_needs',
                    'start_of_support', 'end_of_support', 'date_of_start_of_plan_for_us', 'date_of_change_to_new_plan',
                    'is_latest_plan')
    # all fields are readonly
    readonly_fields = ('created_on', 'updated_on', 'patient', 'date_of_request', 'referent', 'date_of_evaluation',
                       'date_of_notification', 'plan_number', 'decision_number', 'level_of_needs', 'start_of_support',
                       'end_of_support', 'date_of_decision', 'special_package', 'nature_package', 'cash_package',
                       'fmi_right', 'sn_code_aidant', 'link_to_declaration_detail', 'date_of_notification_to_provider')
    fields = ('date_of_start_of_plan_for_us', 'date_of_change_to_new_plan', 'created_on', 'updated_on', 'patient',
              'date_of_request', 'referent', 'date_of_evaluation',
              'date_of_notification', 'plan_number', 'decision_number', 'level_of_needs', 'start_of_support',
              'end_of_support', 'date_of_decision', 'special_package', 'nature_package', 'cash_package',
              'fmi_right', 'sn_code_aidant', 'link_to_declaration_detail', 'date_of_notification_to_provider')
    list_filter = (FilteringPatientsForMedicalCareSummaryPerPatient, 'date_of_decision')
    actions = [create_assurance_dependance_invoices_sept_2024]

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


class InformalCaregiverUnavailabilityInline(admin.StackedInline):
    model = InformalCaregiverUnavailability
    extra = 0


@admin.register(ChangeDeclarationFile)
class ChangeDeclarationFileAdmin(admin.ModelAdmin):
    inlines = [DeclarationDetailInline, InformalCaregiverUnavailabilityInline]
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
    formset = CarePlanDetailForm
    params_occurrence = ModelMultipleChoiceField(queryset=CareOccurrence.objects.all(),
                                                 required=True)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "long_term_care_items":
            kwargs["widget"] = FilteredSelectMultiple(
                db_field.verbose_name, True,
            )
        return super().formfield_for_manytomany(db_field, request, **kwargs)


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
        if request.user.groups.filter(name='clients').exists():
            return None
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
    readonly_fields = ('user', 'created_on', 'updated_on', 'display_plan_concordance')


class AssignedPhysicianInLine(admin.TabularInline):
    extra = 0
    model = AssignedPhysician
    fields = ('assigned_physician', 'main_attending_physician')
    autocomplete_fields = ['assigned_physician']


class ContactPersonInLine(admin.TabularInline):
    extra = 0
    model = ContactPerson
    fields = ('priority', 'contact_name', 'contact_relationship', 'contact_private_phone_nbr',
              'contact_business_phone_nbr', 'contact_address')


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
    class Media:
        js = ('js/admin_reorder_inlines.js',)
    model = TensionAndTemperatureParameters
    formset = TensionAndTemperatureParametersFormset
    fields = ('params_date_time', 'systolic_blood_press', 'diastolic_blood_press', 'heart_pulse', 'temperature',
              'stools_parameter', 'oximeter_saturation', 'vas', 'weight', 'blood_glucose', 'general_remarks', 'user',
              'created_on'
              , "updated_on")
    readonly_fields = ('user', 'created_on', 'updated_on')


def check_access(user, patient):
    print("Checking access for user %s and patient %s" % (user, patient))
    if not user.groups.filter(name='clients').exists():
        return False
    if ClientPatientRelationship.objects.filter(user=user, patient=patient).exists():
        return True
    return False


def list_patients_related_to_client(user):
    if not user.groups.filter(name__contains='client').exists():
        return Patient.objects.all()
    return Patient.objects.filter(clientpatientrelationship__user=user)


@admin.register(MonthlyParameters)
class PatientParametersAdmin(ModelAdminObjectActionsMixin, admin.ModelAdmin):
    fields = ('patient', 'params_year', 'params_month', 'weight')
    list_filter = ('params_month', 'params_year', FilteringPatientsLinkedToParameters)
    list_display = ('patient', 'params_month', 'params_year', 'display_object_actions_list')
    inlines = [TensionAndTemperatureParametersInLine]
    autocomplete_fields = ['patient']

    object_actions = [
        {
            'slug': 'print_all_params',
            'verbose_name': 'Imprimer',
            'form_method': 'GET',
            'view': 'print_all_params',
            'permission': 'view',
        },
        {
            'slug': 'print_glucose_params',
            'verbose_name': 'F. Glycémie',
            'form_method': 'GET',
            'view': 'print_glucose_params',
            'permission': 'view',
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

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user is None:
            return qs.none()
        if request.user.is_superuser or not request.user.groups.filter(name__contains='client').exists():
            return qs.select_related('patient')
        elif request.user.groups.filter(name__contains='client').exists():
            patient_ids = list_patients_related_to_client(request.user).values_list('id', flat=True)
            return qs.filter(Q(patient_id__in=patient_ids))
        else:
            return qs.none()


@admin.register(PatientAnamnesis)
class PatientAnamnesisAdmin(ModelAdminObjectActionsMixin, FieldsetsInlineMixin, admin.ModelAdmin):
    list_display = (
        'patient', 'display_object_actions_list', 'bedsore_count', 'fall_count', 'anticipated_directives', 'updated_on')
    list_filter = ('patient', DeceasedFilter, ClientLeftFilter)
    autocomplete_fields = ['patient']

    actions = ["generate_transfer_doc", "generate_activities_for_march_2024"]

    def generate_transfer_doc(self, request, queryset):
        for anamnesis in queryset:
            return generate_transfer_document(anamnesis)

    def generate_activities_for_march_2024(self, request, queryset):
        for anamnesis in queryset:
            generate_activity_details_from_events(patient=anamnesis.patient, year=2024, month=3)

    def generate_csv_report_2023(self, request, queryset):
        # only for superuser
        if not request.user.is_superuser:
            self.message_user(request, "Only superuser can generate report", level=messages.ERROR)
            return

        # first get all the patients who has no nationality set
        patients = PatientAnamnesis.objects.filter(nationality__isnull=True)
        print("Patients with no nation %s" % patients.count())

        # Get the count of PatientAnamnesis per nationality
        nationality_counts = queryset.values('nationality').annotate(count=Count('nationality'))

        # Prepare to write to a CSV file
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="report_2023.csv"'

        writer = csv.writer(response)
        writer.writerow(['Nationality', 'Count'])

        # if nationality is already met, counter is incremented
        already_met_nationality_dict = {}
        for nationality_count in nationality_counts:
            nationality = nationality_count['nationality']
            count = nationality_count['count']

            if nationality in already_met_nationality_dict:
                already_met_nationality_dict[nationality] += count
            else:
                already_met_nationality_dict[nationality] = count

        for nationality, count in already_met_nationality_dict.items():
            writer.writerow([nationality, count])

        # now I need to count the number patients per gender
        gender_counts = queryset.values('patient__gender').annotate(count=Count('patient__gender')).order_by(
            'patient__gender')
        writer.writerow(['Gender', 'Count'])
        for gc in gender_counts:
            writer.writerow([gc['patient__gender'], gc['count']])

        city_count = queryset.values('patient__city').annotate(count=Count('patient__city')).order_by('patient__city')
        writer.writerow(['City', 'Count'])
        for cc in city_count:
            writer.writerow([cc['patient__city'], cc['count']])
        # now I need count the number of patients per age group
        writer.writerow(['Age Group', 'Count'])
        age_group_dict = {}
        for anamnesis in queryset:
            age_group = anamnesis.patient.age_group
            if age_group in age_group_dict:
                age_group_dict[age_group] += 1
            else:
                age_group_dict[age_group] = 1
        for age_group, count in age_group_dict.items():
            writer.writerow([age_group, count])
        # count the total of activities and multiply by quantity
        writer.writerow(['Activity', 'Count'])
        total = LongTermMonthlyActivityDetail.objects.aggregate(total=Sum(F('quantity'))).get('total')
        # Extract the month from the date field and count the number of instances for each month
        monthly_totals = LongTermMonthlyActivityDetail.objects.annotate(month=ExtractMonth('activity_date')).values(
            'month').annotate(total=Sum(F('quantity'))).order_by('month')

        # Print the total count for each month
        for total in monthly_totals:
            print(f"Month: {total['month']}, Total: {total['total']}")
            writer.writerow([total['month'], total['total']])

        # Group by activity type and count the number of instances for each type
        activity_totals = LongTermMonthlyActivityDetail.objects.values('activity__code').annotate(
            total=Sum(F('quantity'))).order_by('activity__code')
        writer.writerow(['Activity Type', 'Count'])

        # Print the total count for each activity type
        for total in activity_totals:
            print(f"Activity Type: {total['activity__code']}, Total: {total['total']}")
            writer.writerow([total['activity__code'], total['total']])

        return response

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
        {
            'slug': 'print_bedsore_report',
            'verbose_name': 'Rapport Escarres',
            'form_method': 'GET',
            'view': 'print_bedsore_report',
        },
    ]

    readonly_fields = ("created_on", "updated_on",
                       'display_object_actions_detail',
                       'medical_prescriptions_details', 'shared_care_plan'
                       )

    fieldsets_with_inlines = [
        ('Patient', {
            'fields': ('patient', 'nationality', 'civil_status', 'spoken_languages', 'external_doc_link',
                       'birth_place', 'contract_start_date', 'contract_end_date', 'contract_signed_date',
                       'contract_file', 'legal_protection_regimes', 'legal_protection_regimes_doc_link',
                       'legal_protector_name_and_contact',
                       'shared_care_plan', 'help_for_cleaning', 'reason_for_dependence', 'anticipated_directives',
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
                       'informal_caregiver', 'pathologies', 'medical_background', 'treatments', 'allergies',
                       'medical_prescriptions_details'),
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
                       'laundry_manager', 'laundry_drop_location', 'new_laundry_location','hygiene_general_remarks'),
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

    def bedsore_count(self, obj):
        count = obj.patient.bedsore_count()
        if count == 0:
            return count
        url = reverse('admin:invoices_bedsore_changelist') + f'?patient__id__exact={obj.patient.id}'
        return format_html('<a href="{}">{}</a>', url, count)

    bedsore_count.short_description = "Nombre d'escarres"

    def shared_care_plan(self, obj):
        shared_plan = obj.shared_care_plan.get('shared_plan', False)
        sn_code_aidant = obj.shared_care_plan.get('sn_code_aidant', 'N/A')
        checkbox = '<img src="/static/admin/img/icon-yes.svg" alt="True">' if shared_plan else '<img src="/static/admin/img/icon-no.svg" alt="False">'
        if not sn_code_aidant or sn_code_aidant == 'None':
            return mark_safe(f"<b>Partage:</b> {checkbox}")
        return mark_safe(f"<b>Partage:</b> {checkbox}<br><b>SN Code Aidant:</b> {sn_code_aidant}")

    shared_care_plan.short_description = _('Plan de partage')
    def fall_count(self, obj):
        # Assuming the related model for falls is named 'FallDeclaration' and has a ForeignKey to 'Patient'
        count = obj.patient.fall_count()
        if count == 0:
            return count
        url = reverse('admin:dependence_falldeclaration_changelist') + f'?patient__id__exact={obj.patient.id}'
        return format_html('<a href="{}">{}</a>', url, count)

    fall_count.short_description = "Nombre de chutes"

    def print_view(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'patientanamnesis/print_anamnesis2.html', {'obj': obj})

    def print_cover(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        return TemplateResponse(request, 'patientanamnesis/print_cover.html', {'obj': obj})

    def print_bedsore_report(self, request, object_id, form_url='', extra_context=None, action=None):
        from django.template.response import TemplateResponse
        obj = self.get_object(request, object_id)
        bedsore_objects = Bedsore.objects.filter(patient=obj.patient)
        return TemplateResponse(request, 'patientanamnesis/print_bedsore.html', {'bedsore_objects': bedsore_objects})

    def medical_prescriptions_details(self, obj):
        # Get all prescriptions for the patient that have end_date is null or end_date is before today
        current_prescriptions = MedicalPrescription.objects.filter(patient=obj.patient, end_date__isnull=True) | \
                                MedicalPrescription.objects.filter(patient=obj.patient, end_date__lt=timezone.now())
        previous_prescriptions = MedicalPrescription.objects.filter(patient=obj.patient, end_date__isnull=False,
                                                                    end_date__gte=timezone.now())

        details = []
        for prescription in current_prescriptions:
            # Generate the admin URL for the current prescription
            url = reverse('admin:%s_%s_change' % (prescription._meta.app_label, prescription._meta.model_name),
                          args=[prescription.pk])

            # Format the details with the admin URL and title
            detail = format_html('<a href="{}">{}</a><br>'
                                 '{}',
                                 url, str(prescription),
                                 prescription.notes)
            details.append(detail)
        if len(previous_prescriptions) > 0:
            # append a straight html line break
            details.append(format_html('<br><b>Anciennes Prescriptions</b>:<br>'))

        for prescription in previous_prescriptions:
            # Generate the admin URL for the current prescription
            url = reverse('admin:%s_%s_change' % (prescription._meta.app_label, prescription._meta.model_name),
                          args=[prescription.pk])

            # Format the details with the admin URL and title
            detail = format_html('<a href="{}">{}</a><br>'
                                 '{}',
                                 url, str(prescription),
                                 prescription.notes)
            details.append(detail)

        return format_html("<br>".join(details))

        # separate current and previous prescriptions with a blank line
        prescriptions_formatted += [""] if len(current_prescriptions) > 0 and len(previous_prescriptions) > 0 else []
        prescriptions_formatted += [f"{prescription.date} : {prescription.notes}" for prescription
                                    in previous_prescriptions]
        return "\n".join(prescriptions_formatted)

    # Change the display name of the calculated field in the admin interface
    medical_prescriptions_details.short_description = 'Medical Prescriptions Details'


class AAIObjectiveFilesInline(admin.StackedInline):
    model = AAIObjectiveFiles
    extra = 0


@admin.register(AAIObjective)
class AAIObjectiveAdmin(admin.ModelAdmin):
    list_display = (
        'objective', 'patient', 'evaluation_date', 'objective_reaching_date', 'description', 'status')
    readonly_fields = ('created_on', 'updated_on')
    search_fields = ('objective', 'description',)
    inlines = [AAIObjectiveFilesInline]
    list_filter = ('patient', 'status')


class AAITransDetailInLine(admin.TabularInline):
    extra = 0
    model = AAITransDetail
    # I want certain fields to show first
    fields = ('date_time_means_set', 'link_to_objectives', 'means', 'results', 'session_duration',
              'transmission_picture', 'means_paraph')

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == "link_to_objectives":
            if self.parent_obj:
                kwargs["queryset"] = AAIObjective.objects.filter(patient_id=self.parent_obj.patient_id).exclude(status="archived")
            else:
                kwargs["queryset"] = AAIObjective.objects.none()
        return super().formfield_for_manytomany(db_field, request, **kwargs)

    def get_formset(self, request, obj=None, **kwargs):
        self.parent_obj = obj
        return super().get_formset(request, obj, **kwargs)


@admin.register(AAITransmission)
class AAITransmissionAdmin(ModelAdminObjectActionsMixin, admin.ModelAdmin):
    list_display = ('patient', "aai_year", "aai_month", 'transmission_number', 'display_object_actions_list',)
    autocomplete_fields = ['patient']
    readonly_fields = ('user', 'created_on', 'updated_on')
    inlines = [AAITransDetailInLine]
    # filter per patient
    list_filter = ("patient", "aai_year", "aai_month")
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


class LongTermMonthlyActivityDetailInLine(admin.StackedInline):
    extra = 0
    model = LongTermMonthlyActivityDetail


@admin.register(LongTermMonthlyActivity)
class LongTermMonthlyActivityAdmin(admin.ModelAdmin):
    list_display = ('patient', 'month', 'year', 'ratio_days_on_days_of_month')
    list_filter = ('month', 'year')
    autocomplete_fields = ['patient']
    readonly_fields = ('created_on', 'updated_on')
    inlines = [LongTermMonthlyActivityDetailInLine]
    actions = [duplicate_for_next_month, export_selected_to_csv]


@admin.register(LongTermMonthlyActivityFile)
class LongTermMonthlyActivityFileAdmin(admin.ModelAdmin):
    list_display = ('month', 'year', 'has_return_file')
    list_filter = ('month', 'year')
    readonly_fields = ('created_on', 'updated_on')
    form = LongTermMonthlyActivityFileAdminForm


class FallDeclarationReportPictureInLine(admin.TabularInline):
    extra = 0
    model = FallDeclarationReportPicture


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
    inlines = [FallDeclarationReportPictureInLine]
    list_display = ('patient', 'datetimeOfFall', 'display_object_actions_list',)
    list_filter = ('patient', 'datetimeOfFall',)
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
        response = generate_pdf_fall_declaration(queryset)
        return response

    print_document.short_description = _("Print selected objects as PDF")
