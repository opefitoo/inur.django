# -*- coding: utf-8 -*-
from django.http import HttpResponse
from django.utils.translation import gettext_lazy as _
from reportlab.lib.units import cm
from reportlab.platypus.doctemplate import SimpleDocTemplate

from invoices.invoiceitem_pdf import get_doc_elements


def export_to_pdf(modeladmin, request, queryset):
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    # Append invoice number and invoice date
    if len(queryset) != 1:
        _file_name = '-'.join([a.invoice_number for a in queryset.order_by("invoice_number")])
        response['Content-Disposition'] = 'attachment; filename="invoice%s.pdf"' % (_file_name.replace(" ", "")[:150])
    else:
        response['Content-Disposition'] = 'attachment; filename="invoice-%s-%s-%s.pdf"' % (queryset[0].patient.name,
                                                                                           queryset[0].invoice_number,
                                                                                           queryset[
                                                                                               0].invoice_date.strftime(
                                                                                               '%d-%m-%Y'))

    doc = SimpleDocTemplate(response, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
    elements = get_doc_elements(queryset, False)
    doc.build(elements)

    return response


export_to_pdf.short_description = _("CNS Invoice")

def set_invoice_as_paid(modeladmin, request, queryset):
    if request.user.is_superuser:
        queryset.update(invoice_paid=True)
        modeladmin.message_user(request, _("Invoice(s) marked as paid"))
    else:
        modeladmin.message_user(request, _("You are not allowed to do this action"))
set_invoice_as_paid.short_description = _("Mark invoice(s) as paid")

def set_invoice_as_not_sent(modeladmin, request, queryset):
    if request.user.is_superuser:
        queryset.update(invoice_sent=False)
        modeladmin.message_user(request, _("Invoice(s) marked as not sent"))
    else:
        modeladmin.message_user(request, _("You are not allowed to do this action"))

set_invoice_as_not_sent.short_description=_("Mark invoice(s) as not sent")

def set_invoice_as_sent(modeladmin, request, queryset):
    if request.user.is_superuser:
        queryset.update(invoice_sent=True)
        modeladmin.message_user(request, _("Invoice(s) marked as sent"))
    else:
        modeladmin.message_user(request, _("You are not allowed to do this action"))
set_invoice_as_sent.short_description = _("Mark invoice(s) as sent")

def set_invoice_as_not_paid(modeladmin, request, queryset):
    if request.user.is_superuser:
        queryset.update(invoice_paid=False)
        modeladmin.message_user(request, _("Invoice(s) marked as not paid"))
    else:
        modeladmin.message_user(request, _("You are not allowed to do this action"))
set_invoice_as_not_paid.short_description = _("Mark invoice(s) as not paid")


def export_to_pdf_with_medical_prescription_files(modeladmin, request, queryset):
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    # Append invoice number and invoice date
    if len(queryset) != 1:
        _file_name = '-'.join([a.invoice_number for a in queryset.order_by("invoice_number")])
        response['Content-Disposition'] = 'attachment; filename="invoice%s.pdf"' % (_file_name.replace(" ", "")[:150])
    else:
        response['Content-Disposition'] = 'attachment; filename="invoice-%s-%s-%s.pdf"' % (queryset[0].patient.name,
                                                                                           queryset[0].invoice_number,
                                                                                           queryset[
                                                                                               0].invoice_date.strftime(
                                                                                               '%d-%m-%Y'))

    doc = SimpleDocTemplate(response, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
    elements = get_doc_elements(queryset, True)
    doc.build(elements)

    return response


export_to_pdf_with_medical_prescription_files.short_description = "Facture CNS (avec Prescriptions inclues)"
