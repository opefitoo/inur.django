from ajax_select.admin import AjaxSelectAdmin
from django.contrib import admin
from ajax_select import make_ajax_form

from models import CareCode, Prestation, Patient, InvoiceItem, \
    PrivateInvoiceItem


class CareCoreAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'gross_amount')
    search_fields = ['code', 'name']


admin.site.register(CareCode, CareCoreAdmin)


class PatientAdmin(admin.ModelAdmin):
    list_filter = ('city',)
    list_display = ('name', 'first_name', 'phone_number', 'code_sn', 'participation_statutaire')
    search_fields = ['name', 'first_name', 'code_sn']


admin.site.register(Patient, PatientAdmin)


class PrestationAdmin(AjaxSelectAdmin):
    from invaction import create_invoice

    date_hierarchy = 'date'
    list_display = ('patient', 'carecode', 'date')
    search_fields = ['patient__name', 'patient__first_name']
    list_filter = ('patient__name',)
    actions = [create_invoice]
    form = make_ajax_form(Prestation, {'patient': 'patient', 'carecode': 'carecode'})


admin.site.register(Prestation, PrestationAdmin)


class InvoiceItemAdmin(AjaxSelectAdmin):
    from invoices.action import export_to_pdf
    from invoices.action_private_participation import pdf_private_invoice
    from action_private_with_recap import pdf_private_invoice_with_recap
    from invaction import previous_months_invoices_june
    from generate_road_book import generate_road_book_2014

    date_hierarchy = 'invoice_date'
    list_display = ('invoice_number', 'patient', 'invoice_month', 'prestations_invoiced', 'invoice_sent' )
    list_filter = ['invoice_date', 'patient__name', 'invoice_sent']
    search_fields = ['patient']
    actions = [pdf_private_invoice, export_to_pdf, pdf_private_invoice_with_recap, previous_months_invoices_may, generate_road_book_2014]
    form = make_ajax_form(InvoiceItem, {'patient': 'patient_du_mois'})


admin.site.register(InvoiceItem, InvoiceItemAdmin)


class PrivateInvoiceItemAdmin(AjaxSelectAdmin):
    from action_private import pdf_private_invoice
    from action_private_with_recap import pdf_private_invoice_with_recap

    date_hierarchy = 'invoice_date'
    list_display = ('invoice_number', 'private_patient', 'invoice_month', 'prestations_invoiced', 'invoice_sent' )
    list_filter = ['invoice_date', 'private_patient__name', 'invoice_sent']
    search_fields = ['private_patient']
    actions = [pdf_private_invoice, pdf_private_invoice_with_recap]
    form = make_ajax_form(PrivateInvoiceItem, {'private_patient': 'private_patient_a_facturer'})


admin.site.register(PrivateInvoiceItem, PrivateInvoiceItemAdmin)


