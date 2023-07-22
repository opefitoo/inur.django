import calendar
import csv
import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from constance import config
from django.contrib import admin
from django.contrib.admin import TabularInline
from django.contrib.admin.views.main import ChangeList
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, csrf_protect_m
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.checks import messages
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_csv_exports.admin import CSVExportAdmin

from helpers.timesheet import build_use_case_objects
from invoices.action import export_to_pdf, set_invoice_as_sent, set_invoice_as_paid, set_invoice_as_not_paid, \
    set_invoice_as_not_sent, find_all_invoice_items_with_broken_file, \
    find_all_medical_prescriptions_and_merge_them_in_one_file, link_invoice_to_invoice_batch
from invoices.action_private import pdf_private_invoice
from invoices.action_private_participation import pdf_private_invoice_pp
from invoices.actions.certificates import generate_pdf
from invoices.actions.invoices import generer_forfait_aev_mars, generer_forfait_aev_avril, generer_forfait_aev_mai, \
    generer_forfait_aev_june
# from invoices.actions.maps import calculate_distance_matrix
from invoices.actions.print_pdf import do_it, PdfActionType
from invoices.employee import Employee, EmployeeContractDetail, JobPosition, EmployeeAdminFile
from invoices.enums.event import EventTypeEnum
from invoices.enums.holidays import HolidayRequestWorkflowStatus
from invoices.events import EventType, Event, AssignedAdditionalEmployee, ReportPicture, \
    create_or_update_google_calendar, EventList
from invoices.filters.HolidayRequestFilters import FilteringYears, FilteringMonths
from invoices.filters.SmartEmployeeFilter import SmartEmployeeFilter, SmartPatientFilter, SmartMedicalPrescriptionFilter
from invoices.forms import ValidityDateFormSet, HospitalizationFormSet, \
    PrestationInlineFormSet, PatientForm, SimplifiedTimesheetForm, SimplifiedTimesheetDetailForm, EventForm, \
    InvoiceItemForm, MedicalPrescriptionForm, AlternateAddressFormSet
from invoices.gcalendar2 import PrestationGoogleCalendarSurLu
from invoices.googlemessages import post_webhook
from invoices.holidays import HolidayRequest, AbsenceRequestFile
from invoices.models import CareCode, Prestation, Patient, InvoiceItem, Physician, ValidityDate, MedicalPrescription, \
    Hospitalization, InvoiceItemBatch, InvoiceItemEmailLog, PatientAdminFile, InvoiceItemPrescriptionsList, \
    AlternateAddress, Alert
from invoices.modelspackage import InvoicingDetails
from invoices.notifications import notify_holiday_request_validation
from invoices.prefac import generate_flat_file, generate_flat_file_for_control
from invoices.resources import ExpenseCard, Car
from invoices.timesheet import Timesheet, TimesheetDetail, TimesheetTask, \
    SimplifiedTimesheetDetail, SimplifiedTimesheet, PublicHolidayCalendarDetail, PublicHolidayCalendar
from invoices.utils import EventCalendar


@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'is_involved_in_health_care')


@admin.register(TimesheetTask)
class TimesheetTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


# Define an inline admin descriptor for Employee model
# which acts a bit like a singleton
class EmployeeInline(admin.StackedInline):
    model = Employee
    can_delete = False
    verbose_name_plural = 'employee'


# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (EmployeeInline,)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class ValidityDateInline(admin.TabularInline):
    extra = 0
    model = ValidityDate
    formset = ValidityDateFormSet
    fields = ('start_date', 'end_date', 'gross_amount')
    search_fields = ['start_date', 'end_date', 'gross_amount']


@admin.register(CareCode)
class CareCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'reimbursed')
    search_fields = ['code', 'name']
    inlines = [ValidityDateInline]
    # actions = [update_prices_for_jan_2023, update_prices_for_feb_2023, , cleanup_2023]
    # actions = [update_prices_for_april_2022]


class EmployeeContractDetailInline(TabularInline):
    extra = 0
    model = EmployeeContractDetail


class EmployeeAdminFileInline(TabularInline):
    extra = 0
    model = EmployeeAdminFile


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    inlines = [EmployeeContractDetailInline, EmployeeAdminFileInline]
    list_display = ('user', 'start_contract', 'end_contract', 'occupation', 'abbreviation')
    search_fields = ['user__last_name', 'user__first_name', 'user__email']

    def entry_declaration(self, request, queryset):
        counter = 1
        file_data = ""
        for emp in queryset:
            if emp.end_contract:
                pass
            else:
                _last_first_name = "%s %s" % (emp.user.last_name.upper(), emp.user.first_name.capitalize())
                _matricule = "Matricule CNS: %s " % emp.sn_code
                _occupation = "Occupation: %s" % emp.occupation
                _address = "Demeurant au: %s" % emp.address
                # format all dates to dd/mm/yyyy
                _date_entree = "Date Entrée: %s " % emp.start_contract.strftime("%d/%m/%Y")
                # format date to dd/mm/yyyy
                if emp.virtual_career_anniversary_date:
                    _career_anniversary = "Anniversaire de carrière virtuelle: %s" % emp.virtual_career_anniversary_date.strftime(
                        "%d/%m/%Y")
                else:
                    _career_anniversary = "Anniversaire de carrière virtuelle: %s" % "Non défini"
                _citizenship = "Nationalité: %s" % emp.citizenship
                cd = EmployeeContractDetail.objects.filter(employee_link_id=emp.id, end_date__isnull=True).first()
                _contract_situation = "Contrat %s %s h. / semaine - salaire: %s / mois" % (
                    cd.contract_type, cd.number_of_hours, cd.monthly_wage)
                if emp.end_trial_period:
                    _trial_period = "Date fin période d'essai: %s" % emp.end_trial_period.strftime("%d/%m/%Y")
                else:
                    _trial_period = "Date fin période d'essai: %s" % "Non définie"
                _career_rank = "Grade: %s indice %s" % (cd.career_rank, cd.index)
                _bank_account_details = "Numéro de compte bancaire: %s" % emp.bank_account_number
                file_data += f"{_last_first_name} \n {_matricule} \n {_occupation} \n {_citizenship} \n {_address} \n " \
                             f"{_date_entree} {_career_anniversary}\n {_career_rank} \n {_contract_situation} \n " \
                             f"{_trial_period} \n " \
                             f"{_bank_account_details} \n"

            counter += 1
        response = HttpResponse(file_data, content_type='application/text charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="declaration_entree.txt"'
        return response

    def work_certificate(self, request, queryset):
        try:
            return generate_pdf(queryset)
        except ValidationError as ve:
            self.message_user(request, ve.message,
                              level=messages.ERROR)

    def contracts_situation_certificate(self, request, queryset):
        counter = 1
        file_data = ""
        for emp in queryset:
            if emp.end_contract:
                file_data += "%d - %s %s FIN DE CONTRAT LE: %s \n" % (counter, emp.user.last_name.upper(),
                                                                      emp.user.first_name,
                                                                      emp.end_contract.strftime("%d/%m/%Y"))
            else:
                file_data += "%d - %s %s Occupation: %s Temps de travail: %s\n" % (counter,
                                                                                   emp.user.last_name.upper(),
                                                                                   emp.user.first_name,
                                                                                   emp.occupation,
                                                                                   emp.employeecontractdetail_set.filter(
                                                                                       end_date__isnull=True)
                                                                                   .first())
            counter += 1
        response = HttpResponse(file_data, content_type='application/text charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="contract_situation.txt"'
        return response

    work_certificate.short_description = "Certificat de travail"
    contracts_situation_certificate.short_description = "Situation des contrats"

    def export_employees_data_to_csv(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Vous n'êtes pas autorisé à effectuer cette action.",
                              level=messages.ERROR)
            return
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="etp_stats.csv"'
        writer = csv.writer(response)
        _stats_date = datetime.date(2023, 4, 30)
        #_stats_date = datetime.date(2023, 7, 21)
        writer.writerow(['Identifiant anonyme', 'Année de naissance', 'Pays de résidence','Date début du contrat',
                         'Date fin du contrat (si connue)', 'CCT', 'Carrière','Echelon',
                         'Points au %s' % _stats_date.strftime("%d/%m/%Y"), 'Durée de travail hebdomadaire (en heures)',
                         "Structure d'affectation", 'Fonction'])
        for emp in queryset:
            # date 30/04/2023
            _employee_contract = emp.get_contrat_at_date(_stats_date)
            if not _employee_contract:
                continue
            _rank = _employee_contract.career_rank
            # _rank looks like this C5/120 we need to split it
            cct = "-"
            _echelon_rank = []
            if not _rank:
                _echelon_rank.append("NA")
            else:
                _echelon_rank = _rank.split("/")
            if len(_echelon_rank) == 1:
                _echelon_rank.append("NA")
                cct = "-"
            else:
                cct = "SAS"
            # _emp_start in french format date
            _emp_start = _employee_contract.start_date.strftime("%d/%m/%Y")
            _emp_end = _employee_contract.end_date.strftime("%d/%m/%Y") if _employee_contract.end_date else "-"
            writer.writerow([emp.id, emp.birth_date.year, emp.address, _emp_start , _emp_end, cct,
                             _echelon_rank[0], _echelon_rank[1], "", _employee_contract.number_of_hours,
                             "UNIQUE", emp.get_occupation()])
        return response

    # actions = [work_certificate, 'delete_in_google_calendar']
    actions = [work_certificate, contracts_situation_certificate, entry_declaration, export_employees_data_to_csv,]

    def delete_in_google_calendar(self, request, queryset):
        if not request.user.is_superuser:
            return
        counter = 0
        for e in queryset:
            calendar_gcalendar = PrestationGoogleCalendarSurLu()
            counter = calendar_gcalendar.delete_all_events_from_calendar(e.user.email)
        self.message_user(request, "%s évenements supprimés." % counter,
                          level=messages.INFO)


class ExpenseCardDetailInline(TabularInline):
    extra = 0
    model = ExpenseCard


@admin.register(Car)
class CarAdmin(admin.ModelAdmin):
    inlines = [ExpenseCardDetailInline]
    list_display = ('name', 'licence_plate', 'pin_codes', 'geo_localisation_of_car_url', 'car_movement')

    def geo_localisation_of_car_url(self, obj):
        _geo_localisation_of_car = obj.geo_localisation_of_car
        if type(_geo_localisation_of_car) is not tuple and _geo_localisation_of_car.startswith('n/a'):
            return _geo_localisation_of_car
        else:

            url = 'https://maps.google.com/?q=%s,%s' % (_geo_localisation_of_car[1],
                                                        _geo_localisation_of_car[2])
            address = obj.address
            return format_html("<a href='%s'>%s</a>" % (url, address))
        return _geo_localisation_of_car

    geo_localisation_of_car_url.allow_tags = True
    geo_localisation_of_car_url.short_description = "Dernière position connue"


class HospitalizationInline(admin.TabularInline):
    extra = 0
    model = Hospitalization
    formset = HospitalizationFormSet
    fields = ('start_date', 'end_date', 'description')


class PatientAdminFileInline(admin.TabularInline):
    extra = 0
    model = PatientAdminFile

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-file_date')

class AlternateAddressInline(admin.TabularInline):
    model = AlternateAddress
    extra = 0
    formset = AlternateAddressFormSet
class MedicalPrescriptionInlineAdmin(admin.TabularInline):
    extra = 0
    model = MedicalPrescription
    readonly_fields = ('thumbnail_img',)
    autocomplete_fields = ['prescriptor']
    fields = [field.name for field in MedicalPrescription._meta.fields if field.name not in ["id", "file"]]
    ordering = ['-date']

    def scan_preview(self, obj):
        return obj.image_preview

    scan_preview.allow_tags = True


@admin.register(Patient)
class PatientAdmin(CSVExportAdmin):
    list_filter = ('is_under_dependence_insurance',)
    list_display = ('name', 'first_name', 'phone_number', 'code_sn', 'participation_statutaire')
    csv_fields = ['name', 'first_name', 'address', 'zipcode', 'city',
                  'country', 'phone_number', 'email_address', 'date_of_death']
    readonly_fields = ('age', 'link_to_invoices', 'link_to_medical_prescriptions', 'link_to_events')
    search_fields = ['name', 'first_name', 'code_sn', 'zipcode']
    # actions = [calculate_distance_matrix]
    form = PatientForm
    actions = [generer_forfait_aev_mars, generer_forfait_aev_avril, generer_forfait_aev_mai, generer_forfait_aev_june]
    inlines = [HospitalizationInline, MedicalPrescriptionInlineAdmin, PatientAdminFileInline, AlternateAddressInline]

    def link_to_invoices(self, instance):
        url = f'{reverse("admin:invoices_invoiceitem_changelist")}?patient__id={instance.id}'
        return mark_safe('<a href="%s">%s</a>' % (url, "cliquez ici (%d)" % InvoiceItem.objects.filter(
            patient_id=instance.id).count()))

    link_to_invoices.short_description = "Factures client"

    def link_to_medical_prescriptions(self, instance):
        url = f'{reverse("admin:invoices_medicalprescription_changelist")}?patient__id={instance.id}'
        return mark_safe('<a href="%s">%s</a>' % (url, "cliquez ici (%d)" % MedicalPrescription.objects.filter(
            patient_id=instance.id).count()))

    def link_to_events(self, instance):
        url = f'{reverse("admin:invoices_eventlist_changelist")}?event_type_enum__exact=GENERIC&patient__id={instance.id}'
        return mark_safe(
            '<a href="%s">%s</a>' % (url, "Tous les événements Generic du patient ici (%d)" % Event.objects.filter(
                patient_id=instance.id, event_type_enum__exact=EventTypeEnum.GENERIC).count()))

    link_to_medical_prescriptions.short_description = "Ordonnances client"
    link_to_events.short_description = "Evénements client"

    def has_csv_permission(self, request):
        """Only super users can export as CSV"""
        if request.user.is_superuser:
            return True


# @admin.register(Prestation)
# class PrestationAdmin(admin.ModelAdmin):
#     # from invoices.invaction import create_invoice_for_health_insurance
#     def formfield_for_foreignkey(self, db_field, request, **kwargs):
#         if db_field.name == "employee":
#             kwargs["queryset"] = Employee.objects.filter(owner=request.user)
#         return super().formfield_for_foreignkey(db_field, request, **kwargs)
#
#     list_filter = ('invoice_item__patient', 'invoice_item', 'carecode')
#     date_hierarchy = 'date'
#     list_display = ('carecode', 'date')
#     search_fields = ['carecode__code', 'carecode__name']
#     # actions = [create_invoice_for_health_insurance]
#
#
#
#     def get_changeform_initial_data(self, request):
#         initial = {}
#         user = request.user
#         try:
#             employee = user.employee
#             initial['employee'] = employee.id
#         except ObjectDoesNotExist:
#             pass
#
#         return initial
#
#     def get_inline_formsets(self, request, formsets, inline_instances, obj=None):
#         initial = {}
#         print(initial)


@admin.register(Physician)
class PhysicianAdmin(admin.ModelAdmin):
    list_filter = ('city',)
    list_display = ('name', 'first_name', 'phone_number', 'provider_code')
    search_fields = ['name', 'first_name', 'provider_code']


# def migrate_from_g_to_cl(modeladmin, request, queryset):
#     ps = MedicalPrescription.objects.all()
#     for p in ps:
#         if p.file and p.file.url and not p.image_file:
#             print(p.file)
#             local_storage = FileSystemStorage()
#             newfile = ContentFile(p.file.read())
#             relative_path = local_storage.save(p.file.name, newfile)
#
#             print("relative path %s" % relative_path)
#             up = uploader.upload(local_storage.location + "/" + relative_path, folder="medical_prescriptions/")
#             p.image_file = up.get('public_id')
#             p.save()
#             # break


@admin.register(MedicalPrescription)
class MedicalPrescriptionAdmin(admin.ModelAdmin):
    date_hierarchy = 'date'
    list_filter = ('date', 'prescriptor', 'patient')
    # list_display = ('date', 'prescriptor', 'patient', 'link_to_invoices', 'image_preview')
    list_display = ('date', 'prescriptor', 'patient', 'link_to_invoices')
    fields = ('prescriptor', 'patient', 'date', 'end_date', 'notes', 'file_upload', 'thumbnail_img')
    search_fields = ['date', 'prescriptor__name', 'prescriptor__first_name', 'patient__name', 'patient__first_name']
    readonly_fields = ('link_to_invoices',)
    autocomplete_fields = ['prescriptor', 'patient']
    exclude = ('file',)
    form = MedicalPrescriptionForm

    # list_per_page = 5

    # actions = [migrate_from_g_to_cl]
    def link_to_invoices(self, obj):
        count = obj.med_prescription_multi_invoice_items.count()
        url = (
                reverse("admin:invoices_invoiceitem_changelist")
                + "?"
                + urlencode({"prescriptions__medical_prescription__id": f"{obj.id}"})
        )
        return format_html('<a href="{}">{} facture(s)</a>', url, count)

    link_to_invoices.short_description = "Factures client"


class PrestationInline(TabularInline):
    extra = 0
    max_num = InvoiceItem.PRESTATION_LIMIT_MAX
    model = Prestation
    formset = PrestationInlineFormSet
    fields = ('carecode', 'date', 'quantity', 'at_home', 'employee', 'copy', 'delete')
    autocomplete_fields = ['carecode']
    readonly_fields = ('copy', 'delete',)
    search_fields = ['carecode', 'date', 'employee']
    ordering = ['date']
    can_order = True

    class Media:
        js = [
            'admin/js/vendor/jquery/jquery.min.js',
            'admin/js/jquery.init.js',
            "js/inline-copy.js",
            "js/inline-delete.js",
        ]
        css = {
            'all': ('css/inline-prestation.css',)
        }

    def copy(self, obj):
        return format_html("<a href='#' class='copy_inline'>Copy</a>")

    def delete(self, obj):
        url = reverse('delete-prestation')
        return format_html("<a href='%s' class='deletelink' data-prestation_id='%s'>Delete</a>" % (url, obj.id))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "employee":
            kwargs["queryset"] = Employee.objects.all().order_by("-end_contract", "abbreviation")
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    copy.allow_tags = True
    delete.allow_tags = True


@admin.register(InvoicingDetails)
class InvoicingDetailsAdmin(admin.ModelAdmin):
    list_display = ('provider_code', 'name', 'default_invoicing')


class InvoiceItemPrescriptionsListInlines(TabularInline):
    model = InvoiceItemPrescriptionsList
    extra = 0
    fields = ('medical_prescription',)
    autocomplete_fields = ['medical_prescription']


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    class Media:
        css = {
            "all": ("css/invoice_item.css",)
        }

    from invoices.action import export_to_pdf, export_to_pdf_with_medical_prescription_files
    from invoices.action_private import pdf_private_invoice
    from invoices.action_private_participation import pdf_private_invoice_pp
    from invoices.action_depinsurance import export_to_pdf2
    form = InvoiceItemForm
    date_hierarchy = 'invoice_date'
    list_display = ('invoice_number', 'patient', 'invoice_month', 'invoice_sent', 'invoice_paid',
                    'number_of_prestations', 'invoice_details', 'has_medical_prescription')
    list_filter = ['invoice_date', 'invoice_details', 'invoice_sent', 'invoice_paid', SmartPatientFilter,
                   SmartMedicalPrescriptionFilter, 'created_by', 'prescriptions__medical_prescription__id']
    search_fields = ['patient__name', 'patient__first_name', 'invoice_number', 'patient__code_sn']
    readonly_fields = ('medical_prescription_preview', 'created_at', 'updated_at', 'batch')
    autocomplete_fields = ['patient']

    def has_medical_prescription(self, obj):
        return InvoiceItemPrescriptionsList.objects.filter(invoice_item=obj).exists()

    has_medical_prescription.boolean = True

    def cns_invoice_bis(self, request, queryset):
        try:
            return do_it(queryset, action=PdfActionType.CNS)
        except ValidationError as ve:
            self.message_user(request, ve.message,
                              level=messages.ERROR)

    cns_invoice_bis.short_description = "CNS Invoice (new)"

    def pdf_private_invoice_pp_bis(self, request, queryset):
        try:
            return do_it(queryset, action=PdfActionType.PERSONAL_PARTICIPATION)
        except ValidationError as ve:
            self.message_user(request, ve.message,
                              level=messages.ERROR)

    pdf_private_invoice_pp_bis.short_description = "Facture client participation personnelle (new)"

    actions = [link_invoice_to_invoice_batch, generate_flat_file,
               find_all_medical_prescriptions_and_merge_them_in_one_file, find_all_invoice_items_with_broken_file,
               export_to_pdf, export_to_pdf_with_medical_prescription_files, pdf_private_invoice_pp,
               pdf_private_invoice, export_to_pdf2, cns_invoice_bis, pdf_private_invoice_pp_bis, set_invoice_as_sent,
               set_invoice_as_paid, set_invoice_as_not_paid, set_invoice_as_not_sent]
    inlines = [InvoiceItemPrescriptionsListInlines, PrestationInline]
    fieldsets = (
        (None, {
            'fields': ('invoice_number', 'is_private', 'patient', 'invoice_date', 'invoice_details')
        }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': ('accident_id', 'accident_date', 'is_valid', 'validation_comment',
                       'patient_invoice_date', 'invoice_send_date', 'invoice_sent', 'invoice_paid',
                       'medical_prescription', 'created_at', 'updated_at', 'batch'),
        }),
    )
    verbose_name = u"Mémoire d'honoraire"
    verbose_name_plural = u"Mémoires d'honoraire"

    def medical_prescription_preview(self, obj):
        return obj.medical_prescription.image_preview()

    medical_prescription_preview.allow_tags = True

    def changelist_view(self, request, extra_context=None):
        changelist = ChangeList(request,
                                self.model,
                                list(self.get_list_display(request)),
                                self.get_list_display_links(request, self.get_list_display(request)),
                                self.get_list_filter(request),
                                self.date_hierarchy,
                                self.get_search_fields(request),
                                self.list_select_related,
                                self.list_per_page,
                                self.list_max_show_all,
                                self.list_editable,
                                self,
                                self.sortable_by,
                                self.get_search_results)

        # Get a distinct list of patients for the filtered queryset
        patients = list(set(changelist.get_queryset(request).values_list('patient__id', 'patient__name')))
        prescription_ids = list(
            set(changelist.get_queryset(request).values_list('prescriptions__medical_prescription__id', flat=True)))

        medical_prescriptions = MedicalPrescription.objects.filter(id__in=prescription_ids)

        # Attach it to request
        request.dynamic_patient_choices = [(str(patient_id), patient_name) for patient_id, patient_name in patients]
        request.dynamic_medical_prescription_choices = [(str(prescription.id), str(prescription)) for prescription in
                                                        medical_prescriptions]

        return super().changelist_view(request, extra_context)

    def response_change(self, request, obj):
        queryset = InvoiceItem.objects.filter(id=obj.id)
        if "_print_cns" in request.POST:
            return export_to_pdf(self, request, queryset)
            # matching_names_except_this = self.get_queryset(request).filter(name=obj.name).exclude(pk=obj.id)
            # matching_names_except_this.delete()
            # obj.is_unique = True
            # obj.save()
            # self.message_user(request, "This villain is now unique")
            # return HttpResponseRedirect(".")
        if "_print_private_invoice" in request.POST:
            return pdf_private_invoice(self, request, queryset)
        if "_print_personal_participation" in request.POST:
            return pdf_private_invoice_pp(self, request, queryset)
        if "_email_private_invoice" in request.POST:
            if hasattr(queryset[0].patient, 'email_address'):
                if not queryset[0].patient.email_address:
                    self.message_user(request, "Le patient n'a pas d'adresse email définie.",
                                      level=messages.ERROR)
                    return HttpResponseRedirect(request.path)
                if pdf_private_invoice(self, request, queryset, attach_to_email=True):
                    self.message_user(request, "La facture a bien été envoyée au client.",
                                      level=messages.INFO)
                else:
                    self.message_user(request, "La facture n'a pas pu être envoyée au client.",
                                      level=messages.ERROR)
                return HttpResponseRedirect(request.path)
        elif "_email_personal_participation" in request.POST:
            if hasattr(queryset[0].patient, 'email_address'):
                if not queryset[0].patient.email_address:
                    self.message_user(request, "Le patient n'a pas d'adresse email définie.",
                                      level=messages.ERROR)
                    return HttpResponseRedirect(request.path)
            if pdf_private_invoice_pp(self, request, queryset, attach_to_email=True):
                self.message_user(request, "La facture a bien été envoyée au client.",
                                  level=messages.INFO)
            else:
                self.message_user(request, "La facture n'a pas pu être envoyée au client.",
                                  level=messages.ERROR)
            return HttpResponseRedirect(request.path)
        return HttpResponseRedirect(request.path)


class InvoiceItemInlineAdmin(admin.TabularInline):
    show_change_link = True
    max_num = 0
    extra = 0
    model = InvoiceItem
    readonly_fields = ('invoice_number', 'invoice_date',)
    fields = ('invoice_number', 'invoice_date',)
    ordering = ('invoice_date',)
    can_delete = False


@admin.register(InvoiceItemBatch)
class InvoiceItemBatchAdmin(admin.ModelAdmin):
    inlines = [InvoiceItemInlineAdmin]
    readonly_fields = ('created_date', 'modified_date')
    list_display = ('start_date', 'end_date', 'batch_type', 'batch_description')
    actions = [generate_flat_file_for_control]


@admin.register(InvoiceItemEmailLog)
class InvoiceItemEmailLogAdmin(admin.ModelAdmin):
    list_display = ('item', 'sent_at', 'recipient', 'subject')
    list_filter = ('sent_at',)
    search_fields = ('item__invoice_number', 'recipient', 'subject')
    ## display the foreign key as a link
    raw_id_fields = ('item',)
    ## all fields are read-only
    readonly_fields = [f.name for f in InvoiceItemEmailLog._meta.fields]


class TimesheetDetailInline(admin.TabularInline):
    extra = 1
    model = TimesheetDetail
    fields = ('start_date', 'end_date', 'task_description', 'patient',)
    search_fields = ['patient']
    ordering = ['start_date']


@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    fields = ('start_date', 'end_date', 'submitted_date', 'other_details', 'timesheet_validated')
    date_hierarchy = 'end_date'
    inlines = [TimesheetDetailInline]
    list_display = ('start_date', 'end_date', 'timesheet_owner', 'timesheet_validated')
    list_filter = ['employee', ]
    list_select_related = True
    readonly_fields = ('timesheet_validated',)
    verbose_name = 'Time sheet simple'
    verbose_name_plural = 'Time sheets simples'

    def save_model(self, request, obj, form, change):
        if not change:
            current_user = Employee.objects.raw(
                'select * from invoices_employee where user_id = %s' % (request.user.id))
            obj.employee = current_user[0]
        obj.save()

    def timesheet_owner(self, instance):
        return instance.employee.user.username

    def get_queryset(self, request):
        qs = super(TimesheetAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(employee__user=request.user)


class PublicHolidayCalendarDetailInline(admin.TabularInline):
    extra = 1
    model = PublicHolidayCalendarDetail


@admin.register(PublicHolidayCalendar)
class PublicHolidayCalendarAdmin(admin.ModelAdmin):
    inlines = [PublicHolidayCalendarDetailInline]
    verbose_name = u'Congés légaux'
    verbose_name_plural = u'Congés légaux'


class AbsenceRequestFileInline(admin.TabularInline):
    extra = 1
    model = AbsenceRequestFile


@admin.register(HolidayRequest)
class HolidayRequestAdmin(admin.ModelAdmin):
    class Media:
        css = {
            'all': ('css/holiday_request.css',)
        }

    date_hierarchy = 'start_date'
    list_filter = ('employee', FilteringYears, FilteringMonths, 'request_status', 'reason')
    ordering = ['-start_date']
    verbose_name = u"Demande d'absence"
    verbose_name_plural = u"Demandes d'absence"
    inlines = [AbsenceRequestFileInline]

    def holiday_request_status(self, obj):
        if HolidayRequestWorkflowStatus.ACCEPTED == obj.request_status:
            return format_html(
                '<div class="success">%s</div>' % HolidayRequestWorkflowStatus(obj.request_status).name)
        elif HolidayRequestWorkflowStatus.REFUSED == obj.request_status:
            return format_html(
                '<div class="error">%s</div>' % HolidayRequestWorkflowStatus(obj.request_status).name)
        else:
            return format_html(
                '<div class="warn">%s</div>' % HolidayRequestWorkflowStatus(obj.request_status).name)

    def sanity_check(self, obj):
        if obj.start_date.year != obj.end_date.year:
            return format_html(
                '<div class="warn">Attention, la demande concerne deux années différentes.</div>')
        else:
            return ''

    readonly_fields = ('validated_by', 'employee', 'request_creator', 'force_creation',
                       'request_status', 'validator_notes', 'total_days_in_current_year', 'do_not_notify',
                       'total_hours_off_available')
    list_display = ('employee', 'start_date', 'end_date', 'reason', 'hours_taken', 'validated_by',
                    'holiday_request_status', 'request_creator', 'total_days_in_current_year',
                    'sanity_check', 'total_hours_off_available')

    def accept_request(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Vous n'avez pas le droit de valider des %s." % self.verbose_name_plural,
                              level=messages.WARNING)
            return
        rows_updated = 0
        obj: HolidayRequest
        for obj in queryset:
            if obj.request_status != HolidayRequestWorkflowStatus.ACCEPTED:
                try:
                    employee = Employee.objects.get(user_id=request.user.id)
                    obj.validated_by = employee
                    obj.request_status = HolidayRequestWorkflowStatus.ACCEPTED
                    if obj.validator_notes and len(obj.validator_notes) > 0:
                        obj.validator_notes = obj.validator_notes + "\n status: %s by %s on %s" % (
                            obj.request_status,
                            obj.validated_by,
                            timezone.localtime().strftime(
                                '%Y-%m-%dT%H:%M:%S'))
                    else:
                        obj.validator_notes = "status: %s by %s on %s" % (
                            obj.request_status,
                            obj.validated_by,
                            timezone.localtime().strftime(
                                '%Y-%m-%dT%H:%M:%S'))
                    obj.save()
                    notify_holiday_request_validation(obj, request)
                    rows_updated = rows_updated + 1
                except Employee.DoesNotExist:
                    self.message_user(request, "Vous n'avez de profil employé sur l'application pour valider une %s." %
                                      self.verbose_name_plural,
                                      level=messages.ERROR)
                    return
            else:
                ## if request accepted just pass
                pass
        if rows_updated == 1:
            message_bit = u"1 %s a été" % self.verbose_name
        else:
            message_bit = u"%s %s ont été" % (rows_updated, self.verbose_name_plural)
        self.message_user(request, u"%s validé avec succès." % message_bit)

    def refuse_request(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Vous n'avez pas le droit de refuser des %s." % self.verbose_name_plural,
                              level=messages.WARNING)
            return
        rows_updated = 0
        obj: HolidayRequest
        for obj in queryset:
            if obj.request_status != HolidayRequestWorkflowStatus.REFUSED:
                try:
                    employee = Employee.objects.get(user_id=request.user.id)
                    obj.validated_by = employee
                    obj.request_status = HolidayRequestWorkflowStatus.REFUSED
                    obj.request_creator = request.user
                    if len(obj.validator_notes) > 0:
                        obj.validator_notes = obj.validator_notes + "\n status: %s by %s on %s" % (
                            obj.request_status,
                            obj.validated_by,
                            timezone.localtime().strftime(
                                '%Y-%m-%dT%H:%M:%S'))
                    else:
                        obj.validator_notes = "status: %s by %s on %s" % (
                            obj.request_status,
                            obj.validated_by,
                            timezone.localtime().strftime(
                                '%Y-%m-%dT%H:%M:%S'))
                    if not obj.request_creator:
                        obj.request_creator = obj.employee
                    obj.save()
                    notify_holiday_request_validation(obj, request)
                    rows_updated = rows_updated + 1
                except Employee.DoesNotExist:
                    self.message_user(request,
                                      "Vous n'avez de profil employé sur l'application pour refuser une %s." %
                                      self.verbose_name_plural,
                                      level=messages.ERROR)
                    return
            else:
                ## if request already refused just pass
                pass
        if rows_updated == 1:
            message_bit = u"1 %s a été" % self.verbose_name
        else:
            message_bit = u"%s %s ont été" % (rows_updated, self.verbose_name_plural)
        self.message_user(request, u"%s refusée(s) avec succès." % message_bit)

    def response_change(self, request, obj):
        queryset = HolidayRequest.objects.filter(id=obj.id)
        if "_accept_request" in request.POST:
            self.accept_request(request, queryset)
            return HttpResponseRedirect(request.path)
        if "_refuse_request" in request.POST:
            self.refuse_request(request, queryset)
            return HttpResponseRedirect(request.path)
        return HttpResponseRedirect(request.path)

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            if obj.employee.employee.user.id != request.user.id and not 1 != obj.request_status and not request.user.is_superuser:
                return 'employee', 'start_date', 'end_date', 'requested_period', 'reason', 'validated_by', \
                    'hours_taken', 'request_creator'
            elif request.user.is_superuser and not 1 != obj.request_status:
                return [f for f in self.readonly_fields if f not in ['force_creation', 'do_not_notify', 'employee',
                                                                     'request_status',
                                                                     'validator_notes']]
            elif request.user.is_superuser:
                return [f for f in self.readonly_fields if f not in ['force_creation', 'do_not_notify', 'employee',
                                                                     'validator_notes']]
            elif 0 != obj.request_status:
                return 'employee', 'start_date', 'end_date', 'requested_period', 'reason', 'validated_by', \
                    'hours_taken', 'request_creator', 'request_status', 'validator_notes', 'force_creation', 'do_not_notify'

        else:
            if request.user.is_superuser:
                return [f for f in self.readonly_fields if f not in ['force_creation', 'do_not_notify', 'employee',
                                                                     'request_status', 'validator_notes']]
        return self.readonly_fields

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj:
            return request.user.is_superuser or (obj.employee.id == request.user.id and not 1 != obj.request_status)
        else:
            if 'object_id' in request.resolver_match:
                object_id = request.resolver_match.kwargs['object_id']
                holiday_request = HolidayRequest.objects.get(id=object_id)
                return request.user.is_superuser or (
                        holiday_request.employee.id == request.user.id and not 1 != holiday_request.request_status)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.is_superuser:
            if 'validate_or_invalidate_request' in actions:
                del actions['validate_or_invalidate_request']
        return actions


class SimplifiedTimesheetDetailInline(admin.TabularInline):
    extra = 1
    model = SimplifiedTimesheetDetail
    # fields = ('start_date', 'end_date', 'time_delta')
    readonly_fields = ('time_delta',)
    ordering = ['start_date']
    formset = SimplifiedTimesheetDetailForm


def calculate_balance_for_previous_months(month, year, user_id):
    today = datetime.date.today()
    first = today.replace(month=month, year=year).replace(day=1)
    lastMonth = first - datetime.timedelta(days=1)
    previous_timsheets = SimplifiedTimesheet.objects.filter(time_sheet_month=lastMonth.month,
                                                            time_sheet_year=lastMonth.year,
                                                            employee__user_id=user_id,
                                                            timesheet_validated=True)
    for prev_months_tsheet in previous_timsheets:
        return Decimal(round(prev_months_tsheet.hours_should_work_gross_in_sec / 3600, 2)) \
            - prev_months_tsheet.extra_hours_paid_current_month \
            + prev_months_tsheet.extra_hours_balance
    return 0


@admin.register(SimplifiedTimesheet)
class SimplifiedTimesheetAdmin(CSVExportAdmin):
    ordering = ('-time_sheet_year', '-time_sheet_month')
    inlines = [SimplifiedTimesheetDetailInline]
    csv_fields = ['employee', 'time_sheet_year', 'time_sheet_month',
                  'simplifiedtimesheetdetail__start_date',
                  'simplifiedtimesheetdetail__end_date']
    list_display = ('timesheet_owner', 'timesheet_validated', 'time_sheet_year', 'time_sheet_month',
                    'extra_hours_balance')
    list_filter = ['employee', 'time_sheet_year', 'time_sheet_month']
    list_select_related = True
    readonly_fields = ('timesheet_validated', 'total_hours',
                       'total_hours_sundays', 'total_hours_public_holidays', 'total_working_days',
                       'total_legal_working_hours',
                       'total_hours_holidays_taken', 'hours_should_work', 'extra_hours_balance',
                       'extra_hours_paid_current_month', 'created_on', 'updated_on')
    verbose_name = 'Temps de travail'
    verbose_name_plural = 'Temps de travail'
    actions = ['validate_time_sheets', 'timesheet_situation', 'force_cache_clearing', 'build_use_case_objects']
    form = SimplifiedTimesheetForm

    def build_use_case_objects(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request,
                              "Vous n'avez pas le droit de faire cette action des %s." % self.verbose_name_plural)
            return
        file_data = build_use_case_objects(queryset)
        response = HttpResponse(file_data, content_type='application/text charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="test_case.txt"'
        return response

    def timesheet_situation(self, request, queryset):
        _counter = 1
        file_data = ""
        for tsheet in queryset:
            if not tsheet.timesheet_validated:
                self.message_user(request,
                                  "Timesheet %s n'est pas validée, vous devez la valider avant de pouvoir exporter le "
                                  "rapport" % tsheet,
                                  level=messages.ERROR)
                return
            else:
                # take previous months timesheet
                first = tsheet.get_start_date
                lastMonth = first - datetime.timedelta(days=1)
                previous_timsheets = SimplifiedTimesheet.objects.filter(time_sheet_month=lastMonth.month,
                                                                        time_sheet_year=lastMonth.year,
                                                                        employee__user_id=tsheet.user.id,
                                                                        timesheet_validated=True)
                if len(previous_timsheets) == 0:
                    file_data += "\n {counter} - {last_name} {first_name}:\n".format(counter=_counter,
                                                                                     last_name=tsheet.user.last_name.upper(),
                                                                                     first_name=tsheet.user.first_name)
                    if tsheet.extra_hours_paid_current_month:
                        file_data += "\nA travaillé {total_extra} heures supplémentaires.".format(
                            total_extra=tsheet.extra_hours_paid_current_month)
                    if tsheet.total_hours_holidays_and_sickness_taken > 0:
                        file_data += "\n{holidays_sickness_explanation}".format(
                            holidays_sickness_explanation=tsheet.total_hours_holidays_and_sickness_taken_object.beautiful_explanation())
                else:
                    previous_month_tsheet = previous_timsheets.first()
                    file_data += "\n {counter} - {last_name} {first_name}:\n".format(counter=_counter,
                                                                                     last_name=tsheet.user.last_name.upper(),
                                                                                     first_name=tsheet.user.first_name)
                    if tsheet.total_hours_sundays:
                        file_data += " \nA travaillé {hours_sunday} heures des Dimanche".format(
                            hours_sunday=previous_month_tsheet.total_hours_sundays)
                    if tsheet.total_hours_public_holidays:
                        file_data += " \nA travaillé {total_hours_public_holidays} heures des Jours fériés.".format(
                            total_hours_public_holidays=previous_month_tsheet.total_hours_public_holidays)
                    if tsheet.extra_hours_paid_current_month:
                        file_data += " \nA travaillé {total_extra} heures supplémentaires.".format(
                            total_extra=tsheet.extra_hours_paid_current_month)
                    if tsheet.absence_hours_taken()[0] > 0:
                        holiday_sickness_explanation = tsheet.absence_hours_taken()[1].beautiful_explanation()
                        if len(holiday_sickness_explanation) > 0:
                            file_data += holiday_sickness_explanation
                    if previous_month_tsheet.absence_hours_taken()[0] > 0:
                        file_data += "\nPour rappel le mois de %s" % previous_month_tsheet.get_start_date.month
                        holiday_sickness_explanation = previous_month_tsheet.absence_hours_taken()[
                            1].beautiful_explanation()
                        if len(holiday_sickness_explanation) > 0:
                            file_data += holiday_sickness_explanation

            _counter += 1
        response = HttpResponse(file_data, content_type='application/text charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="timesheet_situation.txt"'
        return response

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            if obj.timesheet_validated:
                return self.readonly_fields
            elif request.user.is_superuser and not obj.timesheet_validated:
                return tuple(x for x in self.readonly_fields if x not in ('extra_hours_paid_current_month',
                                                                          'extra_hours_balance'))
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if not change:
            obj.employee = Employee.objects.get(user_id=obj.user.id)
        obj.save()

    def timesheet_owner(self, instance):
        return instance.employee.user.username

    def get_queryset(self, request):
        qs = super(SimplifiedTimesheetAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(employee__user=request.user)

    def validate_time_sheets(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Vous n'avez pas le droit de valider des %s." % self.verbose_name_plural,
                              level=messages.WARNING)
            return
        rows_updated = 0
        obj: SimplifiedTimesheet
        for obj in queryset:
            obj.timesheet_validated = not obj.timesheet_validated
            rows_updated = rows_updated + 1
            obj.extra_hours_balance = calculate_balance_for_previous_months(month=obj.time_sheet_month,
                                                                            year=obj.time_sheet_year,
                                                                            user_id=obj.employee.user.id)
            obj.save()

        if rows_updated == 1:
            message_bit = u"1 time sheet a été"
        else:
            message_bit = u"%s time sheet ont été" % rows_updated
        self.message_user(request, u"%s (in)validé avec succès." % message_bit)

    def change_view(self, request, object_id, extra_context=None):
        if SimplifiedTimesheet.objects.get(pk=object_id).timesheet_validated and not request.user.is_superuser:
            extra_context = extra_context or {}
            extra_context['readonly'] = True
        return super(SimplifiedTimesheetAdmin, self).change_view(request, object_id, extra_context=extra_context)

    def has_change_permission(self, request, obj=None):
        if obj and obj.timesheet_validated and not request.user.is_superuser:
            return False
        return self.has_change_permission

    def has_delete_permission(self, request, obj=None):
        if obj and obj.timesheet_validated and not request.user.is_superuser:
            return False
        return self.has_delete_permission

    def force_cache_clearing(self, request, queryset):
        if request.user.is_superuser:
            cache.clear()
            self.message_user(request, u"Cache refresh OK.", level=messages.INFO)
        else:
            self.message_user(request, u"Not super user.", level=messages.WARNING)


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ['name']


class AssignedAdditionalEmployeeInLine(admin.StackedInline):
    extra = 0
    model = AssignedAdditionalEmployee
    fields = ('assigned_additional_employee',)
    autocomplete_fields = ['assigned_additional_employee']


class ReportPictureInLine(admin.StackedInline):
    extra = 0
    model = ReportPicture
    fields = ('description', 'image',)

    def has_add_permission(self, request, obj):
        return True

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return True

    def has_view_permission(self, request, obj=None):
        return True


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    class Media:
        css = {
            "all": ("css/event.css",)
        }
        js = [
            "js/conditional-event-address.js",
            "js/toggle-period.js",
        ]

    form = EventForm

    list_display = ['day', 'state', 'event_type_enum', 'notes', 'patient']
    readonly_fields = ['created_by', 'created_on', 'calendar_url', 'calendar_id']
    exclude = ('event_type',)
    autocomplete_fields = ['patient']
    change_list_template = 'events/change_list.html'
    change_form_template = 'admin/invoices/event_change_form.html'
    list_filter = (SmartEmployeeFilter,)
    inlines = (AssignedAdditionalEmployeeInLine, ReportPictureInLine)

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if len(form.base_fields) > 0:
                form.base_fields["event_report"].required = True
                form.base_fields["state"].choices = (3, _('Done')), (5, _('Not Done'))

        class ModelFormWithRequest(form):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return form(*args, **kwargs)

        return ModelFormWithRequest

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            if not request.user.is_superuser:
                fs = [field.name for field in Event._meta.fields if field.name != "id"]
                if obj.employees is not None and obj.employees.user.id == request.user.id:
                    return [f for f in fs if f not in ['event_report', 'state']]
                else:
                    return fs
        return self.readonly_fields

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        after_day = request.GET.get('day__gte', None)
        extra_context = extra_context or {}
        employee_id = request.GET.get('employee', None)
        # period = request.GET.get('period', None)

        if not after_day:
            d = datetime.date.today()
        else:
            try:
                split_after_day = after_day.split('-')
                d = datetime.date(year=int(split_after_day[0]), month=int(split_after_day[1]), day=1)
            except:
                d = datetime.date.today()

        previous_month = datetime.date(year=d.year, month=d.month, day=1)  # find first day of current month
        previous_month = previous_month - datetime.timedelta(days=1)  # backs up a single day
        previous_month = datetime.date(year=previous_month.year, month=previous_month.month,
                                       day=1)  # find first day of previous month

        last_day = calendar.monthrange(d.year, d.month)
        next_month = datetime.date(year=d.year, month=d.month, day=last_day[1])  # find last day of current month
        next_month = next_month + datetime.timedelta(days=1)  # forward a single day
        next_month = datetime.date(year=next_month.year, month=next_month.month,
                                   day=1)  # find first day of next month

        extra_context['list_view'] = reverse('admin:invoices_eventlist_changelist')
        extra_context['previous_month'] = reverse('admin:invoices_event_changelist') + '?day__gte=' + str(
            previous_month)
        extra_context['next_month'] = reverse('admin:invoices_event_changelist') + '?day__gte=' + str(next_month)

        cal: EventCalendar = EventCalendar()
        # if "month" == period:
        html_calendar = cal.formatmonth(d.year, d.month, withyear=True, employee_id=employee_id)
        # else:
        #     # html_calendar = cal.formatweek(d.year, d.month, withyear=True, employee_id=employee_id)
        #     html_calendar = cal.formatmonth(d.year, d.month, withyear=True, employee_id=employee_id)
        html_calendar = html_calendar.replace('<td ', '<td  width="150" height="150"')
        extra_context['calendar'] = mark_safe(html_calendar)
        return super(EventAdmin, self).changelist_view(request, extra_context)


@admin.register(EventList)
class EventListAdmin(admin.ModelAdmin):
    list_display = ['day', 'time_start_event', 'time_end_event', 'state', 'event_type_enum', 'patient', 'employees',
                    'created_on']
    change_list_template = 'admin/change_list.html'
    list_filter = ('employees', 'event_type_enum', 'state', 'patient', 'created_by')
    date_hierarchy = 'day'
    exclude = ('event_type',)

    actions = ['safe_delete', 'duplicate_event_for_next_day', 'duplicate_event_for_next_week',
               'delete_in_google_calendar', 'list_orphan_events', 'force_gcalendar_sync',
               'cleanup_events_event_types', 'print_unsynced_events', 'cleanup_all_events_on_google',
               'send_webhook_message']
    inlines = (ReportPictureInLine,)
    autocomplete_fields = ['patient']

    form = EventForm

    def safe_delete(self, request, queryset):
        if not request.user.is_superuser:
            return
        for e in queryset:
            e.delete()

    def send_webhook_message(self, request, queryset):
        if not request.user.is_superuser:
            return
        for e in queryset:
            post_webhook(employees=e.employees, patient=e.patient, event_report=e.event_report, state=e.state,
                         event_date=datetime.datetime.combine(e.day, e.time_start_event).astimezone(ZoneInfo("Europe"
                                                                                                             "/Luxembourg")))

    def list_orphan_events(self, request, queryset):
        if not request.user.is_superuser:
            return
        for e in queryset:
            e.display_unconnected_events()

    def duplicate_event_for_next_week(self, request, queryset):
        if not request.user.is_superuser:
            return
        # only one event at a time
        events_duplicated = []
        if len(queryset) < 6:
            print("duplicating %s events [direct call]" % len(queryset))
            for e in queryset:
                events_duplicated.append(e.duplicate_event_for_next_day(7))
            self.message_user(request, "Duplicated %s events" % len(events_duplicated))
            # redirect to list filtering on duplicated events
            return HttpResponseRedirect(
                reverse('admin:invoices_eventlist_changelist') + '?id__in=' + ','.join(
                    [str(e.id) for e in events_duplicated]))
        else:
            print("duplicating %s events [redis rq call]" % len(queryset))
            # create array with all selected events
            from invoices.processors.tasks import duplicate_event_for_next_day_for_several_events
            duplicate_event_for_next_day_for_several_events.delay([e for e in queryset], request.user, number_of_days=7)
            self.message_user(request,
                              "Il y a %s événements à dupliquer pour j + 7, cela peut prendre quelques minutes, vous allez recevoir une notification par google chat à la fin de la création" % len(
                                  queryset))

    def duplicate_event_for_next_day(self, request, queryset):
        if not request.user.is_superuser:
            return
        # only one event at a time
        events_duplicated = []
        if len(queryset) < 6:
            print("duplicating %s events [direct call]" % len(queryset))
            for e in queryset:
                events_duplicated.append(e.duplicate_event_for_next_day(1))
            self.message_user(request, "Duplicated %s events" % len(events_duplicated))
            # redirect to list filtering on duplicated events
            return HttpResponseRedirect(
                reverse('admin:invoices_eventlist_changelist') + '?id__in=' + ','.join(
                    [str(e.id) for e in events_duplicated]))
        else:
            print("duplicating %s events [redis rq call]" % len(queryset))
            # create array with all selected events
            from invoices.processors.tasks import duplicate_event_for_next_day_for_several_events
            duplicate_event_for_next_day_for_several_events.delay([e for e in queryset], request.user, number_of_days=1)
            self.message_user(request,
                              "Il y a %s événements à dupliquer pour j + 1, cela peut prendre quelques minutes, vous allez recevoir une notification par google chat à la fin de la création" % len(
                                  queryset))

    def cleanup_all_events_on_google(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Must be super user", level=messages.ERROR)
            return
        for e in queryset:
            result = e.cleanup_all_events_on_google(dry_run=False)
            self.message_user(request, "Deleted %s messages from Google calendar " % len(result),
                              level=messages.WARNING)

    def force_gcalendar_sync(self, request, queryset):
        if not request.user.is_superuser:
            return
        evts_synced = []
        for e in queryset:
            cal = create_or_update_google_calendar(e)
            e.calendar_id = cal.get('id')
            e.calendar_url = cal.get('htmlLink')
            evts_synced.append(e.calendar_url)
            e.save()
        self.message_user(request, "%s évenements synchronisés. : %s" % (len(evts_synced), evts_synced),
                          level=messages.INFO)

    def print_unsynced_events(self, request, queryset):
        if not request.user.is_superuser:
            return
        evts_not_synced = []
        for e in queryset:
            if 'http://a.sur.lu' == e.calendar_url and e.calendar_id == 0:
                evts_not_synced.append(e)
        if len(evts_not_synced) > 0:
            self.message_user(request, "%s évenements non synchronisés. : %s" % (len(evts_not_synced), evts_not_synced),
                              level=messages.WARNING)
        else:
            self.message_user(request, "Tous les évenements sont synchronisés.",
                              level=messages.INFO)

    def cleanup_events_event_types(self, request, queryset):
        if not request.user.is_superuser:
            return
        evts_cleaned = []
        for e in Event.objects.filter(event_type=EventType.objects.get(id=1)):
            if e.event_type_enum != EventTypeEnum.BIRTHDAY:
                e.event_type_enum = EventTypeEnum.BIRTHDAY
                e.save()
                evts_cleaned.append(e)
        if len(evts_cleaned) > 0:
            self.message_user(request, "%s événements nettoyés. : %s" % (len(evts_cleaned), evts_cleaned),
                              level=messages.WARNING)
        else:
            self.message_user(request, "Tous les évenements sont propres.",
                              level=messages.INFO)

    def get_queryset(self, request):
        queryset = super(EventListAdmin, self).get_queryset(request)
        today = datetime.datetime.now()
        if request.user.is_superuser:
            return Event.objects.all()
        else:
            # Display only today's and yesterday's events for non admin users
            return queryset.filter(employees__user_id=request.user.id).exclude(state=3).exclude(state=5).filter(
                day__year=today.year).filter(day__month=today.month).filter(day__day__gte=today.day - 1).order_by(
                "-day")

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if len(form.base_fields) > 0:
                form.base_fields["event_report"].required = True
                form.base_fields["state"].choices = (3, _('Done')), (5, _('Not Done')), (6, _('Cancelled'))

        class ModelFormWithRequest(form):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return form(*args, **kwargs)

        return ModelFormWithRequest

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            if not request.user.is_superuser:
                fs = [field.name for field in Event._meta.fields if field.name != "id"]
                if obj.employees.user.id == request.user.id:
                    return [f for f in fs if f not in ['event_report', 'state', '']]
                else:
                    return fs
        return self.readonly_fields

    def get_inlines(self, request, obj):
        return [ReportPictureInLine]


class EventWeekList(Event):
    class Meta:
        proxy = True
        verbose_name = "Nouveau Plannig (Ne modifiez pas les événements à partir d'ici)"
        verbose_name_plural = "Nouveaux Plannigs (Ne modifiez pas les événements à partir d'ici)"


@admin.register(EventWeekList)
class EventWeekListAdmin(admin.ModelAdmin):
    class Media:
        css = {
            "all": ("css/main.min.css",)
        }
        js = [
            "js/main.min.js",
        ]

    list_display = ['day', 'time_start_event', 'time_end_event', 'state', 'event_type_enum', 'patient', 'employees']
    exclude = ('event_type',)
    change_list_template = 'events/calendar.html'
    change_form_template = 'admin/invoices/event_change_form.html'
    list_filter = ('employees', 'event_type_enum', 'state', 'patient', 'created_by')
    date_hierarchy = 'day'

    actions = ['safe_delete', 'delete_in_google_calendar', 'list_orphan_events']
    readonly_fields = ['created_by', 'created_on', 'calendar_url', 'calendar_id']

    context = {}
    form = EventForm

    @csrf_protect_m
    def changelist_view(self, request, extra_context=None):
        raw_list = Event.objects.filter(day__month=datetime.date.today().month).order_by("employees_id")
        # object_list = (Event.objects
        #                .values()
        #                .annotate(employees=Count('employees_id'))
        #                .order_by()
        #                )
        #
        # results = Event.objects.raw(
        #     'SELECT ie.employees_id, ie.* FROM invoices_event ie order by ie.employees_id desc')
        # object_list = {}
        # for r in raw_list:
        #     if r.employees:
        #         l = object_list.get(r.employees.id)
        #         if l:
        #             l.append(r)
        #             # dd[r.employees.id] = l
        #         else:
        #             object_list[r.employees.id] = [r]

        extra_context = {'object_list': raw_list, 'root_url': config.ROOT_URL, 'form': self.form}

        return super(EventWeekListAdmin, self).changelist_view(request, extra_context)

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if not request.user.is_superuser:
            if len(form.base_fields) > 0:
                form.base_fields["event_report"].required = True
                form.base_fields["state"].choices = (3, _('Done')), (5, _('Not Done'))

        class ModelFormWithRequest(form):
            def __new__(cls, *args, **kwargs):
                kwargs['request'] = request
                return form(*args, **kwargs)

        return ModelFormWithRequest

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            if not request.user.is_superuser:
                fs = [field.name for field in Event._meta.fields if field.name != "id"]
                if obj.employees.user.id == request.user.id:
                    return [f for f in fs if f not in ['event_report', 'state']]
                else:
                    return fs
        return self.readonly_fields


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ('text_alert', 'alert_level', 'date_alert', 'is_read', 'date_read', 'is_active', 'link_to_object', 'user')
    list_filter = ('alert_level', 'is_read', 'is_active', 'user')
    search_fields = ('text_alert', 'user__username')
    readonly_fields = ('date_alert', 'date_read', 'alert_created_by')
    # if not superuser show only alerts assigned by user
    def get_queryset(self, request):
        qs = super(AlertAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(user=request.user, is_active=True)
    # non superuser can only modify alerts assigned to him and only field is_read
    def get_readonly_fields(self, request, obj=None):
        if not request.user.is_superuser:
            return [f.name for f in self.model._meta.fields if f.name not in ['is_read', 'comment']]
        return self.readonly_fields
