import pytz
from django.http import HttpResponse
import typing
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, PageBreak


from invoices.actions.elements import CnsNursingCareDetail, NurseDetails, InvoiceHeaderData, PatientAbstractDetails, \
    InvoiceNumberDate, AnotherBodyPage, RowDict
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
    elements = []
    summary_data = []
    already_added_images = []
    for invoice_item in queryset.order_by("invoice_number"):
        elements.extend(get_invoice_hdr(invoice_item))
        elements.append(get_body_elements(invoice_item))
        elements.append(PageBreak())
    return elements


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


def get_body_elements(invoice: InvoiceItem):
    # Splitting the invoice given cares by group of max 20
    dd = [invoice.prestations.all().order_by("date", "carecode__name")[i:i + 20] for i in
          range(0, len(invoice.prestations.all()), 20)]
    data = []

    for prestations in dd:
        _inv = invoice.invoice_number + (
            ("" + str(dd.index(prestations) + 1) + invoice.invoice_date.strftime('%m%Y')) if len(dd) > 1 else "")
        data.append(('Num. titre', 'Prestation', 'Date', 'Nombre', 'Brut', 'Net', 'Heure', 'P. Pers', 'Executant'))
        pytz_luxembourg = pytz.timezone("Europe/Luxembourg")
        care_details = [CnsNursingCareDetail]
        my_dict = RowDict()
        for idx, presta in enumerate(prestations):
            if presta.carecode.reimbursed:
                __nursing_care_dtl = CnsNursingCareDetail(code=presta.carecode.code, care_datetime=presta.date,
                                                          quantity=1,
                                                          net_price=presta.carecode.net_amount(presta.date,
                                                                                               invoice.patient.is_private,
                                                                                               (
                                                                                                       invoice.patient.participation_statutaire
                                                                                                       and invoice.patient.age > 18)),
                                                          provider_code=presta.employee.provider_code,
                                                          gross_price=presta.carecode.gross_amount(presta.date))
                my_dict.add(idx+1, __nursing_care_dtl)
                care_details.append(__nursing_care_dtl)
        another_b = AnotherBodyPage(rows=my_dict)
        # S = another_b.to_array()
        # body_detail_page = BodyDetailsPage(nursing_cares=care_details)
        return another_b.get_table()


def _build_invoices(invoice: InvoiceItem, prestations: [Prestation], invoice_number, invoice_date, accident_id,
                    accident_date):
    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
    # import pydevd; pydevd.settrace()
    elements = []
    i = 0
    data = []

    data.append(('Num. titre', 'Prestation', 'Date', 'Nombre', 'Brut', 'Net', 'Heure', 'P. Pers', 'Executant'))
    pytz_luxembourg = pytz.timezone("Europe/Luxembourg")
    for presta in prestations:
        if presta.carecode.reimbursed:
            __nursing_care_dtl = CnsNursingCareDetail()
            __nursing_care_dtl.code = presta.carecode.code
            __nursing_care_dtl.care_datetime = presta.date
            __nursing_care_dtl.quantity = 1
            __nursing_care_dtl.net_price = presta.carecode.net_amount(presta.date, invoice.patient.is_private,
                                                                      (invoice.patient.participation_statutaire
                                                                       and invoice.patient.age > 18))
            __nursing_care_dtl.provider_code = presta.employee.provider_code

            i += 1
            data.append((i, presta.carecode.code,
                         (pytz_luxembourg.normalize(presta.date)).strftime('%d/%m/%Y'),
                         '1',
                         presta.carecode.gross_amount(presta.date),
                         presta.carecode.net_amount(presta.date, presta.patient.is_private,
                                                    (presta.patient.participation_statutaire
                                                     and presta.patient.age > 18)),
                         (pytz_luxembourg.normalize(presta.date)).strftime('%H:%M'),
                         "",
                         presta.employee.provider_code))

    for x in range(len(data), 22):
        data.append((x, '', '', '', '', '', '', '', ''))

    newData = []
    for y in range(0, len(data) - 1):
        newData.append(data[y])
        if (y % 10 == 0 and y != 0):
            _gross_sum = _compute_sum(data[y - 9:y + 1], 4)
            _net_sum = _compute_sum(data[y - 9:y + 1], 5)
            newData.append(('', '', '', 'Sous-Total', _gross_sum, _net_sum, '', '', ''))
    newData.append(('', '', '', 'Total', _compute_sum(data[1:], 4), _compute_sum(data[1:], 5), '', '', ''))

    elements.append(invoice_hdr_tbl)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    elements.append(Spacer(1, 18))
    elements.append(
        Paragraph(u"Mémoire d'Honoraires Num. %s en date du : %s" % (invoice_number, invoice_date), styles['Center']))
    elements.append(Spacer(1, 18))

    _2derniers_cases = Table([["", "Paiement Direct"]], [1 * cm, 4 * cm], 1 * [0.5 * cm], hAlign='LEFT')
    _2derniers_cases.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'RIGHT'),
                                          ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                          ('FONTSIZE', (0, 0), (-1, -1), 9),
                                          ('BOX', (0, 0), (0, 0), 0.75, colors.black),
                                          ('SPAN', (1, 1), (1, 2)),
                                          ]))

    elements.append(Spacer(1, 18))

    elements.append(_2derniers_cases)
    _2derniers_cases = Table([["", "Tiers payant"]], [1 * cm, 4 * cm], 1 * [0.5 * cm], hAlign='LEFT')
    _2derniers_cases.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'RIGHT'),
                                          ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                          ('FONTSIZE', (0, 0), (-1, -1), 9),
                                          ('BOX', (0, 0), (0, 0), 0.75, colors.black),
                                          ('SPAN', (1, 1), (1, 2)),
                                          ]))
    elements.append(Spacer(1, 18))
    elements.append(_2derniers_cases)
    elements.append(Spacer(1, 18))

    _pouracquit_signature = Table([["Pour acquit, le:", "Signature et cachet"]], [10 * cm, 10 * cm], 1 * [0.5 * cm],
                                  hAlign='LEFT')

    elements.append(_pouracquit_signature)
    return {"elements": elements, "invoice_number": invoice_number,
            "patient_name": patientName + " " + patientFirstName, "invoice_amount": newData[23][5]}
