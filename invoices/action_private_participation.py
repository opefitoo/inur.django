# -*- coding: utf-8 -*-
import decimal
from io import BytesIO

from constance import config
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus.doctemplate import SimpleDocTemplate
from reportlab.platypus.flowables import Spacer, PageBreak
from reportlab.platypus.para import Paragraph
from reportlab.platypus.tables import Table, TableStyle

from invoices import settings
from invoices.xero.exceptions import XeroTokenRefreshError
from invoices.xero.invoice import create_xero_invoice


def pdf_private_invoice_pp(modeladmin, request, queryset, attach_to_email=False,
                           only_to_xero_or_any_accounting_system=False, return_elements=False):
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    # Append invoice number and invoice date
    # generate payment reference as a hash of the invoice numbers
    payment_reference_hash = ""
    for qs in queryset.order_by("invoice_number"):
        payment_reference_hash += str(qs.invoice_number)
    _payment_ref = "PP%s" % str(abs(hash(payment_reference_hash)))[:6]
    if len(queryset) != 1:
        _file_name = '-'.join([a.invoice_number for a in queryset.order_by("invoice_number")])
        _recap_date = now().date().strftime('%d-%m-%Y')
        response['Content-Disposition'] = 'attachment; filename="invoice%s.pdf"' % (_file_name.replace(" ", "")[:150])
    else:
        _payment_ref = "PP%s %s" % (queryset[0].invoice_number, queryset[0].invoice_date.strftime('%d.%m.%Y'))
        _recap_date = queryset[0].invoice_date.strftime('%d-%m-%Y')
        response['Content-Disposition'] = 'attachment; filename="invoice-%s-%s-%s-part-personnelle.pdf"' % (
            queryset[0].patient.name,
            queryset[0].invoice_number,
            queryset[0].invoice_date.strftime('%d-%m-%Y'))

    elements = []
    if attach_to_email:
        io_buffer = BytesIO()
        doc = SimpleDocTemplate(io_buffer, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
        # _payment_ref = "PP-MX-%s" % _file_name.replace(" ", "")[:10]
    else:
        doc = SimpleDocTemplate(response, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
        # _payment_ref = "PP-%s" % _file_name.replace(" ", "")[:10]

    recapitulatif_data = []

    for qs in queryset.order_by("invoice_number"):
        dd = [qs.prestations.all().order_by("date", "carecode__name")[i:i + 20] for i in
              range(0, len(qs.prestations.all()), 20)]
        for _prestations in dd:
            _inv = qs.invoice_number + (
                ("" + str(dd.index(_prestations) + 1) + qs.invoice_date.strftime('%m%Y')) if len(dd) > 1 else "")
            invoice_elmts = _build_invoices(_prestations,
                                      _inv,
                                      qs.invoice_date,
                                      qs.medical_prescription,
                                      qs.accident_id,
                                      qs.accident_date,
                                      qs.patient_invoice_date,
                                      qs.patient)
            if invoice_elmts["elements"] is None:
                continue
            elements.extend(invoice_elmts["elements"])
            recapitulatif_data.append((invoice_elmts["invoice_number"], invoice_elmts["patient_name"], invoice_elmts["invoice_pp"]))
            elements.append(PageBreak())

    elements.extend(_build_recap(_recap_date, _payment_ref, recapitulatif_data))
    if return_elements:
        return elements
    doc.build(elements)
    if attach_to_email:
        subject = "Votre Facture %s" % _payment_ref
        message = "Bonjour, \nVeuillez trouver ci-joint la facture en pièce jointe. \nCordialement \n -- \n%s \n%s " \
                  "%s\n%s\n%s" % (config.NURSE_NAME, config.NURSE_ADDRESS, config.NURSE_ZIP_CODE_CITY,
                                  config.NURSE_PHONE_NUMBER, config.MAIN_BANK_ACCOUNT)
        if only_to_xero_or_any_accounting_system:
            try:
                create_xero_invoice(queryset[0], _result["invoice_pp"], io_buffer.getvalue())
            except XeroTokenRefreshError as e:
                return redirect('xero-auth')
        else:
            emails = [qs.patient.email_address]
            if config.CC_EMAIL_SENT:
                emails += config.CC_EMAIL_SENT.split(",")
            mail = EmailMessage(subject, message, settings.EMAIL_HOST_USER, emails)
            mail.attach("%s.pdf" % _payment_ref, io_buffer.getvalue(), 'application/pdf')
            from invoices.models import InvoiceItemEmailLog
            try:
                status = mail.send(fail_silently=False)
                InvoiceItemEmailLog.objects.create(item=qs, recipient=qs.patient.email_address,
                                                   subject=subject, body=message, cc=emails, status=status)
                return status
            except Exception as e:
                print(e)
                InvoiceItemEmailLog.objects.create(item=qs, recipient=qs.patient.email_address,
                                                   subject=subject, body=message, cc=emails, status=0, error=e)
                return False
        io_buffer.close()
    return response


def _build_invoices(prestations, invoice_number, invoice_date, prescription_date, accident_id, accident_date,
                    patient_invoice_date, patient):
    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
    elements = []
    i = 0
    data = []
    patientSocNumber = ''
    patientNameAndFirstName = ''
    patientName = '';
    patient_first_name = '';
    patient_address = ''

    data.append(('Num. titre', 'Prestation', 'Date', 'Nombre', 'Brut', 'CNS', 'Part. Client'))
    for presta in prestations:
        i += 1
        patientSocNumber = patient.code_sn
        patientNameAndFirstName = patient
        patientName = patient.name
        patient_first_name = patient.first_name
        patient_address = patient.address
        patientZipCode = patient.zipcode
        patientCity = patient.city
        data.append((i, presta.carecode.code,
                     (presta.date).strftime('%d/%m/%Y'),
                     '1',
                     round(presta.carecode.gross_amount(presta.date), 2),
                     presta.carecode.net_amount(presta.date,
                                                patient.is_private,
                                                patient.participation_statutaire
                                                and patient.age > 18),
                     "%10.2f" % (decimal.Decimal(presta.carecode.gross_amount(presta.date)) -
                                 decimal.Decimal(presta.carecode.net_amount(presta.date,
                                                                            patient.is_private,
                                                                            patient.participation_statutaire)))))

    for x in range(len(data), 22):
        data.append((x, '', '', '', '', '', ''))

    newData = []
    for y in range(0, len(data) - 1):
        newData.append(data[y])
        if (y % 10 == 0 and y != 0):
            _gross_sum = _compute_sum(data[y - 9:y + 1], 4)
            _net_sum = _compute_sum(data[y - 9:y + 1], 5)
            _part_sum = _compute_sum(data[y - 9:y + 1], 6)
            newData.append(('', '', '', 'Sous-Total', "%10.2f" % _gross_sum, "%10.2f" % _net_sum, "%10.2f" % _part_sum))
    _total_facture = _compute_sum(data[1:], 5)
    _participation_personnelle = decimal.Decimal(_compute_sum(data[1:], 4)) - decimal.Decimal(_total_facture)
    if _participation_personnelle <= 0:
        return {"elements": None
            , "invoice_number": None
            , "patient_name": patientName + " " + patient_first_name
            , "invoice_amount": None
            , "invoice_pp": None}
    newData.append(('', '', '', 'Total', "%10.2f" % _compute_sum(data[1:], 4), "%10.2f" % _compute_sum(data[1:], 5),
                    "%10.2f" % _compute_sum(data[1:], 6)))

    headerData = [['IDENTIFICATION DU FOURNISSEUR DE SOINS DE SANTE\n'
                   + "{0}\n{1}\n{2}\n{3}".format(config.NURSE_NAME,
                                                 config.NURSE_ADDRESS,
                                                 config.NURSE_ZIP_CODE_CITY,
                                                 config.NURSE_PHONE_NUMBER),
                   'CODE DU FOURNISSEUR DE SOINS DE SANTE\n{0}'.format(config.MAIN_NURSE_CODE)
                   ],
                  [u'Matricule patient: %s' % patientSocNumber.strip() + "\n"
                   + u'Nom et Prénom du patient: %s' % patientNameAndFirstName,
                   u'Nom: %s' % patientName.strip() + '\n'
                   + u'Prénom: %s' % patient_first_name.strip() + '\n'
                   + u'Rue: %s' % patient_address.strip() + '\n'
                   + u'Code postal: %s' % patientZipCode.strip() + '\n'
                   + u'Ville: %s' % patientCity.strip()],
                  [u'Date accident: %s\n' % (accident_date if accident_date else "")
                   + u'Num. accident: %s' % (accident_id if accident_id else "")]]

    headerTable = Table(headerData, 2 * [10 * cm], [2.5 * cm, 1 * cm, 1.5 * cm])
    headerTable.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                                     ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                                     ('FONTSIZE', (0, 0), (-1, -1), 9),
                                     ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                                     ('SPAN', (1, 1), (1, 2)),
                                     ]))

    table = Table(newData, 9 * [2.5 * cm], 24 * [0.5 * cm])
    table.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                               ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('ALIGN', (0, -1), (-6, -1), 'RIGHT'),
                               ('INNERGRID', (0, -1), (-6, -1), 0, colors.white),
                               ('ALIGN', (0, -2), (-6, -2), 'RIGHT'),
                               ('INNERGRID', (0, -2), (-6, -2), 0, colors.white),
                               ('FONTSIZE', (0, 0), (-1, -1), 8),
                               ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                               ]))

    elements.append(headerTable)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    elements.append(Spacer(1, 18))
    if (prescription_date is not None):
        elements.append(Paragraph(u"Mémoire d'Honoraires Num. %s en date du : %s Ordonnance du %s " % (
            invoice_number, invoice_date, prescription_date), styles['Heading4']))
    else:
        elements.append(Paragraph(u"Mémoire d'Honoraires Num. %s en date du : %s " % (invoice_number, invoice_date),
                                  styles['Heading4']))

    elements.append(Spacer(1, 18))

    elements.append(table)

    elements.append(Spacer(1, 18))

    _total_a_payer = Table([["Total participation personnelle:", "%10.2f Euros" % _participation_personnelle]],
                           [10 * cm, 5 * cm], 1 * [0.5 * cm], hAlign='LEFT')
    elements.append(Spacer(1, 18))
    elements.append(_total_a_payer)
    elements.append(Spacer(1, 18))

    elements.append(Spacer(1, 10))

    if patient_invoice_date is not None:
        import locale
        locale.setlocale(locale.LC_ALL, "fr_FR.UTF-8")
        elements.append(Table([[u"Date envoi de la présente facture: %s " % patient_invoice_date.strftime(
            '%d %B %Y')]], [10 * cm], 1 * [0.5 * cm], hAlign='LEFT'))
        elements.append(Spacer(1, 10))

    return {"elements": elements
        , "invoice_number": invoice_number
        , "patient_name": patientName + " " + patient_first_name
        , "invoice_amount": newData[23][5]
        , "invoice_pp": newData[23][6]}


pdf_private_invoice_pp.short_description = _("Personal participation")


def _compute_sum(data, position):
    sum = 0
    for x in data:
        if x[position] != "":
            sum += decimal.Decimal(x[position])
    return sum


def _build_recap(_recap_date, _recap_ref, recaps):
    """
    """
    elements = []

    _intro = Table([[
        u"Veuillez trouver ci-joint le récapitulatif des factures ainsi que le montant total à payer"]],
        [10 * cm, 5 * cm], 1 * [0.5 * cm], hAlign='LEFT')
    elements.append(_intro)
    elements.append(Spacer(1, 18))

    data = []
    i = 0
    data.append(("N d'ordre", u"Note no°", u"Nom et prénom", "Montant"))
    total = 0.0
    _invoice_nrs = "";
    for recap in recaps:
        i += 1
        data.append((i, recap[0], recap[1], recap[2]))
        total = decimal.Decimal(total) + decimal.Decimal(recap[2])
        _invoice_nrs += "-" + recap[0]
    data.append(("", "", u"à reporter", round(total, 2), ""))

    table = Table(data, [2 * cm, 3 * cm, 7 * cm, 3 * cm], (i + 2) * [0.75 * cm])
    table.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                               ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('FONTSIZE', (0, 0), (-1, -1), 9),
                               ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                               ]))
    elements.append(table)

    elements.append(Spacer(1, 18))

    elements.append(Spacer(1, 18))
    _infos_iban = Table([["Lors du virement, veuillez indiquer la référence : %s " % _recap_ref]],
                        [10 * cm], 1 * [0.5 * cm], hAlign='LEFT')
    _date_infos = Table([["Date facture : %s " % _recap_date]], [10 * cm], 1 * [0.5 * cm], hAlign='LEFT')

    elements.append(_date_infos)
    elements.append(Spacer(1, 18))
    elements.append(_infos_iban)
    elements.append(Spacer(1, 18))
    _total_a_payer = Table([["Total " + u"à" + " payer:", "%10.2f Euros" % total]], [10 * cm, 5 * cm], 1 * [0.5 * cm],
                           hAlign='LEFT')
    elements.append(_total_a_payer)
    elements.append(Spacer(1, 18))

    _infos_iban = Table([[u"Numéro IBAN: %s" % config.MAIN_BANK_ACCOUNT]], [10 * cm], 1 * [0.5 * cm], hAlign='LEFT')
    elements.append(_infos_iban)

    return elements
