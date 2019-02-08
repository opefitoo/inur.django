# -*- coding: utf-8 -*-
from django.http import HttpResponse
from invoices.invoiceitem_pdf_bis import get_doc_elements
from reportlab.lib.units import cm
from reportlab.platypus.doctemplate import SimpleDocTemplate
import hashlib


def export_to_pdf2(modeladmin, request, queryset):
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    # Append invoice number and invoice date
    if len(queryset) != 1:
        _file_name = '-'.join([a.invoice_number for a in queryset.order_by("invoice_number")])
        payment_ref = hashlib.sha1(_file_name.encode("UTF-8")).hexdigest()[:10]

        response['Content-Disposition'] = 'attachment; filename="invoice%s.pdf"' % (_file_name.replace(" ", "")[:150])
    else:
        response['Content-Disposition'] = 'attachment; filename="invoice-%s-%s-%s.pdf"' % (queryset[0].patient.name,
                                                                                           queryset[0].invoice_number,
                                                                                           queryset[
                                                                                               0].invoice_date.strftime(
                                                                                               '%d-%m-%Y'))

    doc = SimpleDocTemplate(response, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
    elements = get_doc_elements(queryset, payment_ref)
    doc.build(elements)

    return response


export_to_pdf2.short_description = "Facture Forfaits soins infi."
