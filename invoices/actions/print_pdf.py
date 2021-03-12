import copy

import pytz
from django.core.exceptions import ValidationError
from django.http import HttpResponse
import typing
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, PageBreak

from invoices.actions.elements import CnsNursingCareDetail, NurseDetails, InvoiceHeaderData, PatientAbstractDetails, \
    InvoiceNumberDate, MedicalCareBodyPage, RowDict, build_cns_bottom_elements, SummaryData, SummaryDataTable, \
    CnsFinalPage
from invoices.models import Prestation, InvoiceItem


def do_it(modeladmin, request, queryset):
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


def get_doc_elements(queryset, med_p=False):
    pdf_elements = []
    summary_data = []
    already_added_images = []
    invoice_item: InvoiceItem
    order_number = 1
    previous_invoice: InvoiceItem = None
    for invoice_item in queryset.order_by("invoice_number"):
        if previous_invoice and previous_invoice.invoice_details.id != invoice_item.invoice_details.id:
            raise ValidationError(
                "%s has a different provider code then %s, cannot print CNS batch with "
                "different provider codes " % (previous_invoice, invoice_item))
        previous_invoice = invoice_item
        if invoice_item.prestations.count() <= 20:
            pdf_elements.extend(get_invoice_hdr(invoice_item))
            body_elements = get_body_elements(invoice_item)
            pdf_elements.append(body_elements.get_table())
            pdf_elements += build_cns_bottom_elements()
            pdf_elements.append(PageBreak())
            summary_data.append(SummaryData(order_number=order_number,
                                            invoice_num=invoice_item.invoice_number,
                                            patient_name=invoice_item.patient,
                                            total_amount=body_elements.fst_gross_sub_total +
                                                         body_elements.snd_gross_sub_total))
            order_number += 1

        else:
            prestations_splits = [invoice_item.prestations.all().order_by("date", "carecode__name")[i:i + 20] for i in
                                  range(0, len(invoice_item.prestations.all()), 20)]
            i = 1
            for ps in prestations_splits:
                v_invoice: InvoiceItem = copy.copy(invoice_item)
                v_invoice.invoice_number = "%s - %s" % (invoice_item.invoice_number, i)
                i += 1
                pdf_elements.extend(get_invoice_hdr(v_invoice))
                body_elements = get_body_elements(v_invoice, [p for p in ps])
                pdf_elements.append(body_elements.get_table())
                print("%s %s" % (v_invoice, v_invoice.number_of_prestations))
                pdf_elements += build_cns_bottom_elements()
                pdf_elements.append(PageBreak())
                summary_data.append(SummaryData(order_number=order_number,
                                                invoice_num=v_invoice.invoice_number,
                                                patient_name=invoice_item.patient,
                                                total_amount=body_elements.fst_gross_sub_total +
                                                             body_elements.snd_gross_sub_total))
                order_number += 1
    summary_data_table: SummaryDataTable = SummaryDataTable(summary_data)
    pdf_elements += summary_data_table.get_table()
    pdf_elements.append(PageBreak())
    pdf_elements += CnsFinalPage(total_summary=summary_data_table.total_summary,
                                 order_number=len(summary_data_table.summary_data_list),
                                 invoicing_details=previous_invoice.invoice_details).get_table()
    return pdf_elements


def get_invoice_hdr(invoice: InvoiceItem) -> [object]:
    nursing_dtl = NurseDetails(fullname=invoice.invoice_details.name, address=invoice.invoice_details.address,
                               zipcode_city=invoice.invoice_details.zipcode_city,
                               phone_number=invoice.invoice_details.phone_number,
                               provider_code=invoice.invoice_details.provider_code)
    patients_dtl = PatientAbstractDetails(sn_code=invoice.patient.code_sn, fst_nm=invoice.patient.first_name,
                                          last_nm=invoice.patient.name, adr=invoice.patient.address,
                                          zip_code=invoice.patient.zipcode, city=invoice.patient.city,
                                          accident_date=invoice.accident_date, accident_num=invoice.accident_id)
    invoice_nbr_date = InvoiceNumberDate(invoice_number=invoice.invoice_number, invoice_date=invoice.invoice_date)
    invoice_hdr_data = InvoiceHeaderData(nurse_details=nursing_dtl, patient_details=patients_dtl,
                                         invoice_nbr_date=invoice_nbr_date)
    return invoice_hdr_data.build_element()


def get_body_elements(invoice: InvoiceItem, splitted_prestations=None):
    care_details = [CnsNursingCareDetail]
    my_dict = RowDict()
    for idx, presta in enumerate(splitted_prestations if splitted_prestations else invoice.prestations.all()):
        if presta.carecode.reimbursed:
            __nursing_care_dtl = CnsNursingCareDetail(code=presta.carecode.code, care_datetime=presta.date,
                                                      quantity=1,
                                                      net_price=presta.carecode.net_amount(presta.date,
                                                                                           invoice.patient.is_private,
                                                                                           (
                                                                                                   invoice.patient.participation_statutaire
                                                                                                   and invoice.patient.age > 18)),
                                                      provider_code=presta.employee.provider_code if presta.employee
                                                      else presta.invoice_item.invoice_details.provider_code,
                                                      gross_price=presta.carecode.gross_amount(presta.date))
            my_dict.add(idx + 1, __nursing_care_dtl)
            care_details.append(__nursing_care_dtl)
    return MedicalCareBodyPage(rows=my_dict)
    # return medical_care_body.get_table()
