from ajax_select import make_ajax_form, make_ajax_field
from ajax_select.admin import AjaxSelectAdmin, AjaxSelectAdminTabularInline, AjaxSelectAdminStackedInline
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from models import CareCode, Prestation, Patient, InvoiceItem, \
    PrivateInvoiceItem, InvoiceItemPrestation
from timesheet import Employee, JobPosition, Timesheet, TimesheetDetail, TimesheetTask

from django_admin_bootstrapped.admin.models import SortableInline


class JobPostionAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


admin.site.register(JobPosition, JobPostionAdmin)


class TimesheetTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')


admin.site.register(TimesheetTask, TimesheetTaskAdmin)


# Define an inline admin descriptor for Employee model
# which acts a bit like a singleton
class EmployeeInline(SortableInline, admin.StackedInline):
    model = Employee
    can_delete = False
    verbose_name_plural = 'employee'


# Define a new User admin
class UserAdmin(BaseUserAdmin):
    inlines = (EmployeeInline,)


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


class CareCoreAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'gross_amount', 'reimbursed')
    search_fields = ['code', 'name']


admin.site.register(CareCode, CareCoreAdmin)


class PatientAdmin(admin.ModelAdmin):
    from generate_pacifico_invoices import generate_pacifico
    list_filter = ('city',)
    list_display = ('name', 'first_name', 'phone_number', 'code_sn', 'participation_statutaire')
    search_fields = ['name', 'first_name', 'code_sn']
    actions = [generate_pacifico]


admin.site.register(Patient, PatientAdmin)


class PrestationAdmin(AjaxSelectAdmin):
    from invaction import create_invoice_for_health_insurance, create_invoice_for_client_no_irs_reimbursed

    date_hierarchy = 'date'
    list_display = ('carecode', 'date')
    search_fields = ['carecode__code', 'carecode__name']
    #list_filter = ('patient__name',)
    actions = [create_invoice_for_health_insurance, create_invoice_for_client_no_irs_reimbursed]
    form = make_ajax_form(Prestation, {'carecode': 'carecode'})


admin.site.register(Prestation, PrestationAdmin)


class InvoiceItemPrestationInline(AjaxSelectAdminStackedInline):
    model = InvoiceItemPrestation
    search_fields = ['prestation__patient__name', 'prestation__patient__first_name', ]
    extra = 1
    form = make_ajax_form(InvoiceItemPrestation, {
        'invoiceitem': 'invoiceitem',
        'prestation': 'prestation'
    },
                          show_help_text=True)


class InvoiceItemAdmin(AjaxSelectAdmin):
    from invoices.action import export_to_pdf
    from action_private import pdf_private_invoice
    from action_private_participation import pdf_private_invoice_pp
    from invaction import previous_months_invoices_april, previous_months_invoices_july_2017
    from generate_pacifico_invoices import niedercorn_avril_mai_2017
    from invaction import syncro_clients
    date_hierarchy = 'invoice_date'
    # list_display = ('invoice_number', 'patient', 'invoice_month', 'prestations_invoiced', 'invoice_sent',)
    list_display = ('invoice_number', 'patient', 'invoice_month', 'invoice_sent')
    list_filter = ['invoice_date', 'patient__name', 'invoice_sent']
    search_fields = ['patient__name', 'patient__first_name']
    actions = [export_to_pdf, pdf_private_invoice_pp, pdf_private_invoice, syncro_clients,
               previous_months_invoices_april, previous_months_invoices_july_2017, niedercorn_avril_mai_2017]
    form = make_ajax_form(InvoiceItem, {'patient': 'patient_du_mois'})
    inlines = [InvoiceItemPrestationInline]


admin.site.register(InvoiceItem, InvoiceItemAdmin)


class PrivateInvoiceItemAdmin(AjaxSelectAdmin):
    from action_private import pdf_private_invoice
    from action_private_with_recap import pdf_private_invoice_with_recap

    date_hierarchy = 'invoice_date'
    # list_display = ('invoice_number', 'private_patient', 'invoice_month', 'prestations_invoiced', 'invoice_sent' )
    list_display = ('invoice_number', 'private_patient', 'invoice_month', 'invoice_sent')
    list_filter = ['invoice_date', 'private_patient__name', 'invoice_sent']
    search_fields = ['private_patient__name', 'private_patient__first_name']
    actions = [pdf_private_invoice]
    form = make_ajax_form(PrivateInvoiceItem, {'private_patient': 'private_patient_a_facturer'})


admin.site.register(PrivateInvoiceItem, PrivateInvoiceItemAdmin)


class TimesheetDetailInline(AjaxSelectAdminTabularInline):
    model = TimesheetDetail
    fields = ('start_date', 'end_date', 'task_description', 'patient',)
    search_fields = ['patient']
    extra = 1
    form = make_ajax_form(TimesheetDetail, {'patient': 'patient'})

    model = TimesheetDetail
    form = make_ajax_form(TimesheetDetail, {
        'patient': 'patient',
        'task_description': 'task_description'
    },
                          show_help_text=True)
    extra = 2


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
