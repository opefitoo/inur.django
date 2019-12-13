import calendar
from datetime import datetime

from django.contrib import admin
from django.contrib.admin import TabularInline
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.core.checks import messages
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils.functional import curry
from django.utils.html import format_html

from invoices.invaction import make_private, \
    export_xml
from invoices.forms import ValidityDateFormSet, PrestationForm, InvoiceItemForm, HospitalizationFormSet, \
    PrestationInlineFormSet, \
    PatientForm, SimplifiedTimesheetForm, SimplifiedTimesheetDetailForm
from invoices.models import CareCode, Prestation, Patient, InvoiceItem, Physician, ValidityDate, MedicalPrescription, \
    Hospitalization, InvoiceItemBatch
from invoices.timesheet import Employee, JobPosition, Timesheet, TimesheetDetail, TimesheetTask, \
    SimplifiedTimesheetDetail, SimplifiedTimesheet, PublicHolidayCalendarDetail, PublicHolidayCalendar, \
    EmployeeContractDetail


class JobPostionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


admin.site.register(JobPosition, JobPostionAdmin)


class TimesheetTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


admin.site.register(TimesheetTask, TimesheetTaskAdmin)


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


class CareCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'reimbursed')
    search_fields = ['code', 'name']
    actions = [make_private, export_xml]
    inlines = [ValidityDateInline]


admin.site.register(CareCode, CareCodeAdmin)


class EmployeeContractDetailInline(TabularInline):
    extra = 0
    model = EmployeeContractDetail


class EmployeeAdmin(admin.ModelAdmin):
    inlines = [EmployeeContractDetailInline]
    list_display = ('user', 'start_contract', 'end_contract', 'occupation')
    search_fields = ['user', 'occupation']


admin.site.register(Employee, EmployeeAdmin)


class HospitalizationInline(admin.TabularInline):
    extra = 0
    model = Hospitalization
    formset = HospitalizationFormSet
    fields = ('start_date', 'end_date', 'description')


class MedicalPrescriptionInlineAdmin(admin.TabularInline):
    extra = 0
    model = MedicalPrescription
    readonly_fields = ('scan_preview',)

    def scan_preview(self, obj):
        return obj.image_preview(300, 300)

    scan_preview.allow_tags = True


class PatientAdmin(admin.ModelAdmin):
    list_filter = ('city',)
    list_display = ('name', 'first_name', 'phone_number', 'code_sn', 'participation_statutaire')
    readonly_fields = ('age',)
    search_fields = ['name', 'first_name', 'code_sn']
    form = PatientForm
    actions = []
    inlines = [HospitalizationInline, MedicalPrescriptionInlineAdmin]


admin.site.register(Patient, PatientAdmin)


class PrestationAdmin(admin.ModelAdmin):
    from invoices.invaction import create_invoice_for_health_insurance

    list_filter = ('invoice_item__patient', 'invoice_item', 'carecode')
    date_hierarchy = 'date'
    list_display = ('carecode', 'date')
    search_fields = ['carecode__code', 'carecode__name']
    actions = [create_invoice_for_health_insurance]

    form = PrestationForm

    def get_changeform_initial_data(self, request):
        initial = {}
        user = request.user
        try:
            employee = user.employee
            initial['employee'] = employee.id
        except ObjectDoesNotExist:
            pass

        return initial


class PhysicianAdmin(admin.ModelAdmin):
    list_filter = ('city',)
    list_display = ('name', 'first_name', 'phone_number', 'provider_code')
    search_fields = ['name', 'first_name', 'code_sn']


admin.site.register(Physician, PhysicianAdmin)


class MedicalPrescriptionAdmin(admin.ModelAdmin):
    list_filter = ('date',)
    list_display = ('date', 'prescriptor', 'patient', 'file')
    search_fields = ['date', 'prescriptor__name', 'prescriptor__firstname', 'patient__name', 'patient__first_name']
    readonly_fields = ('image_preview',)


admin.site.register(MedicalPrescription, MedicalPrescriptionAdmin)


class PrestationInline(TabularInline):
    extra = 0
    max_num = InvoiceItem.PRESTATION_LIMIT_MAX
    model = Prestation
    formset = PrestationInlineFormSet
    form = PrestationForm
    fields = ('carecode', 'date', 'quantity', 'at_home', 'employee', 'copy', 'delete')
    readonly_fields = ('copy', 'delete')
    search_fields = ['carecode', 'date', 'employee']
    can_delete = False
    ordering = ['date']

    class Media:
        js = [
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

    copy.allow_tags = True
    delete.allow_tags = True

    def get_formset(self, request, obj=None, **kwargs):
        initial = []
        formset = super(PrestationInline, self).get_formset(request, obj, **kwargs)
        user = request.user
        try:
            employee = user.employee
            if request.method == "GET":
                formset.form.base_fields['employee'].initial = employee.id
                initial.append({
                    'employee': employee.id,
                })
        except ObjectDoesNotExist:
            pass

        formset.__init__ = curry(formset.__init__, initial=initial)

        return formset


class InvoiceItemAdmin(admin.ModelAdmin):
    from invoices.action import export_to_pdf
    from invoices.action_private import pdf_private_invoice
    from invoices.action_private_participation import pdf_private_invoice_pp
    from invoices.action_depinsurance import export_to_pdf2
    form = InvoiceItemForm
    date_hierarchy = 'invoice_date'
    list_display = ('invoice_number', 'patient', 'invoice_month', 'invoice_sent')
    list_filter = ['invoice_date', 'patient__name', 'invoice_sent']
    search_fields = ['patient__name', 'patient__first_name']
    readonly_fields = ('medical_prescription_preview',)
    actions = [export_to_pdf, pdf_private_invoice_pp, pdf_private_invoice, export_to_pdf2]
    inlines = [PrestationInline]
    fieldsets = (
        (None, {
            'fields': ('invoice_number', 'is_private', 'patient', 'invoice_date')
        }),
        ('Advanced options', {
            'classes': ('collapse',),
            'fields': ('accident_id', 'accident_date', 'is_valid', 'validation_comment',
                       'patient_invoice_date', 'invoice_send_date', 'invoice_sent', 'invoice_paid',
                       'medical_prescription'),
        }),
    )
    verbose_name = u"Mémoire d'honoraire"
    verbose_name_plural = u"Mémoires d'honoraire"

    def medical_prescription_preview(self, obj):
        return obj.medical_prescription.image_preview()

    medical_prescription_preview.allow_tags = True


admin.site.register(InvoiceItem, InvoiceItemAdmin)


class InvoiceItemInlineAdmin(admin.TabularInline):
    show_change_link = True
    max_num = 0
    extra = 0
    model = InvoiceItem
    fields = ('invoice_date', 'is_valid', 'validation_comment')
    readonly_fields = ('invoice_date',)
    can_delete = False


class InvoiceItemBatchAdmin(admin.ModelAdmin):
    inlines = [InvoiceItemInlineAdmin]
    readonly_fields = ('file',)


admin.site.register(InvoiceItemBatch, InvoiceItemBatchAdmin)


class TimesheetDetailInline(admin.TabularInline):
    extra = 1
    model = TimesheetDetail
    fields = ('start_date', 'end_date', 'task_description', 'patient',)
    search_fields = ['patient']
    ordering = ['start_date']


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


admin.site.register(Timesheet, TimesheetAdmin)


class PublicHolidayCalendarDetailInline(admin.TabularInline):
    extra = 1
    model = PublicHolidayCalendarDetail


class PublicHolidayCalendarAdmin(admin.ModelAdmin):
    inlines = [PublicHolidayCalendarDetailInline]
    verbose_name = u'Congés légaux'
    verbose_name_plural = u'Congés légaux'


admin.site.register(PublicHolidayCalendar, PublicHolidayCalendarAdmin)


class SimplifiedTimesheetDetailInline(admin.TabularInline):
    extra = 1
    model = SimplifiedTimesheetDetail
    fields = ('start_date', 'end_date',)
    search_fields = ['patient']
    ordering = ['start_date']
    form = SimplifiedTimesheetDetailForm


class SimplifiedTimesheetAdmin(admin.ModelAdmin):
    ordering = ('-time_sheet_year', '-time_sheet_month')
    inlines = [SimplifiedTimesheetDetailInline]
    list_display = ('timesheet_owner', 'timesheet_validated', 'time_sheet_year', 'time_sheet_month')
    list_filter = ['employee', ]
    list_select_related = True
    readonly_fields = ('timesheet_validated', 'total_hours',
                       'total_hours_sundays', 'total_hours_public_holidays', 'total_working_days', 'hours_should_work',)
    verbose_name = 'Temps de travail'
    verbose_name_plural = 'Temps de travail'
    actions = ['validate_time_sheets', ]
    form = SimplifiedTimesheetForm

    def save_model(self, request, obj, form, change):
        if not change:
            current_user = Employee.objects.raw(
                'select * from invoices_employee where user_id = %s' % (request.user.id))
            obj.employee = current_user[0]
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
            obj.save()
            rows_updated = rows_updated + 1
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


# class SimplifiedTimesheetAdmin2(admin.ModelAdmin):
#     fields = ('start_date', 'end_date', 'timesheet_validated', 'total_hours', 'total_hours_saturdays',
#               'total_hours_sundays')
#     date_hierarchy = 'end_date'
#     inlines = [SimplifiedTimesheetDetailInline]
#     list_display = ('start_date', 'end_date', 'timesheet_owner', 'timesheet_validated', 'total_hours',
#                     'total_hours_saturdays', 'total_hours_sundays')
#     list_filter = ['employee', ]
#     list_select_related = True
#     readonly_fields = ('timesheet_validated', 'total_hours', 'total_hours_saturdays', 'total_hours_sundays')
#     verbose_name = 'Time sheet simple'
#     verbose_name_plural = 'Time sheets simples'
#     change_form_template = 'admin/preview_template.html'
#
#     # def calculate_total_hours(self, instance):
#     #     return format_html_join(
#     #         mark_safe('<br>'),
#     #         '{}',
#     #         SimplifiedTimesheet.objects.calculate_total_hours().get('total')
#     #     ) or mark_safe("<span class='errors'>I can't determine this address.</span>")
#
#     def save_model(self, request, obj, form, change):
#         if not change:
#             current_user = Employee.objects.raw(
#                 'select * from invoices_employee where user_id = %s' % (request.user.id))
#             obj.employee = current_user[0]
#         obj.save()
#
#     def timesheet_owner(self, instance):
#         return instance.employee.user.username
#
#     def get_queryset(self, request):
#         qs = super(SimplifiedTimesheetAdmin2, self).get_queryset(request)
#         if request.user.is_superuser:
#             return qs
#         return qs.filter(employee__user=request.user)
#

admin.site.register(SimplifiedTimesheet, SimplifiedTimesheetAdmin)
