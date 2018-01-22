from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.utils.functional import curry
from django.core.urlresolvers import reverse

from invoices.invaction import apply_start_date_2017, apply_start_date_2015, apply_start_date_2013, make_private
from forms import ValidityDateFormSet, PrestationForm, InvoiceItemForm, HospitalizationFormSet, PrestationInlineFormSet, \
    PatientForm
from models import CareCode, Prestation, Patient, InvoiceItem, Physician, ValidityDate, MedicalPrescription, \
    Hospitalization, InvoiceItemBatch
from timesheet import Employee, JobPosition, Timesheet, TimesheetDetail, TimesheetTask


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


class CareCoreAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'reimbursed')
    search_fields = ['code', 'name']
    actions = [apply_start_date_2017, apply_start_date_2015, apply_start_date_2013, make_private]
    inlines = [ValidityDateInline]


admin.site.register(CareCode, CareCoreAdmin)


class EmployeeAdmin(admin.ModelAdmin):
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
    readonly_fields = ('scan_preview', )

    def scan_preview(self, obj):
        return obj.image_preview(300, 300)

    scan_preview.allow_tags = True


class PatientAdmin(admin.ModelAdmin):
    from generate_pacifico_invoices import generate_pacifico
    list_filter = ('city',)
    list_display = ('name', 'first_name', 'phone_number', 'code_sn', 'participation_statutaire')
    search_fields = ['name', 'first_name', 'code_sn']
    form = PatientForm
    actions = [generate_pacifico]
    inlines = [HospitalizationInline, MedicalPrescriptionInlineAdmin]


admin.site.register(Patient, PatientAdmin)


class PrestationAdmin(admin.ModelAdmin):
    from invaction import create_invoice_for_health_insurance, create_invoice_for_client_no_irs_reimbursed

    list_filter = ('invoice_item__patient', 'invoice_item', 'carecode')
    date_hierarchy = 'date'
    list_display = ('carecode', 'date')
    search_fields = ['carecode__code', 'carecode__name']
    actions = [create_invoice_for_health_insurance, create_invoice_for_client_no_irs_reimbursed]

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
    list_display = ('date', 'prescriptor','patient','file')
    search_fields = ['date', 'prescriptor__name', 'prescriptor__firstname', 'patient__name', 'patient__first_name']
    readonly_fields = ('image_preview',)


admin.site.register(MedicalPrescription, MedicalPrescriptionAdmin)


class PrestationInline(admin.TabularInline):
    extra = 0
    max_num = InvoiceItem.PRESTATION_LIMIT_MAX
    model = Prestation
    formset = PrestationInlineFormSet
    form = PrestationForm
    fields = ('carecode', 'date', 'quantity', 'at_home', 'employee', 'copy', 'delete')
    readonly_fields = ('copy', 'delete')
    search_fields = ['carecode', 'date', 'employee']
    can_delete = False

    class Media:
        js = [
            "js/inline-copy.js",
            "js/inline-delete.js",
        ]
        css = {
            'all': ('css/inline-prestation.css',)
        }

    def copy(self, obj):
        return "<a href='#' class='copy_inline'>Copy</a>"

    def delete(self, obj):
        url = reverse('delete-prestation')

        return "<a href='%s' class='delete_inline' data-prestation_id='%s'>Delete</a>" % (url, obj.id)

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
    from action_private import pdf_private_invoice
    from action_private_participation import pdf_private_invoice_pp
    from invaction import previous_months_invoices_april, previous_months_invoices_july_2017
    from generate_pacifico_invoices import niedercorn_avril_mai_2017
    from road_book_csv import generate_road_book_2016
    form = InvoiceItemForm
    date_hierarchy = 'invoice_date'
    list_display = ('invoice_number', 'patient', 'invoice_month', 'invoice_sent')
    list_filter = ['invoice_date', 'patient__name', 'invoice_sent']
    search_fields = ['patient__name', 'patient__first_name']
    readonly_fields = ('medical_prescription_preview',)
    actions = [export_to_pdf, pdf_private_invoice_pp, pdf_private_invoice]
    inlines = [PrestationInline]

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
    extra = 2
    model = TimesheetDetail
    fields = ('start_date', 'end_date', 'task_description', 'patient',)
    search_fields = ['patient']


class TimesheetAdmin(admin.ModelAdmin):
    fields = ('start_date', 'end_date', 'submitted_date', 'other_details', 'timesheet_validated')
    inlines = [TimesheetDetailInline]
    list_display = ('start_date', 'end_date', 'timesheet_owner', 'timesheet_validated')
    list_select_related = True
    readonly_fields = ('timesheet_validated',)

    def save_model(self, request, obj, form, change):
        if not change:
            currentUser = Employee.objects.raw('select * from invoices_employee where user_id = %s' % (request.user.id))
            obj.employee = currentUser[0]
        obj.save()

    def timesheet_owner(self, instance):
        return instance.employee.user.username


admin.site.register(Timesheet, TimesheetAdmin)
