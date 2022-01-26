# -*- coding: utf-8 -*-
import sys
from io import BytesIO

from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.utils.timezone import now
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus.doctemplate import SimpleDocTemplate
from reportlab.platypus.flowables import Spacer, PageBreak
from reportlab.platypus.para import Paragraph
from reportlab.platypus.tables import Table, TableStyle
import pytz
import decimal
from constance import config
from django.utils.translation import gettext_lazy as _

from invoices import settings


def pdf_private_invoice(modeladmin, request, queryset, attach_to_email=False):
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    # Append invoice number and invoice date
    if len(queryset) != 1:
        _file_name = '-'.join([a.invoice_number for a in queryset.order_by("invoice_number")])
        response['Content-Disposition'] = 'attachment; filename="invoice%s.pdf"' % (_file_name.replace(" ", "")[:150])
    else:
        if hasattr(queryset[0], 'private_patient'):
            response['Content-Disposition'] = 'attachment; filename="invoice-%s-%s-%s.pdf"' % (
                queryset[0].private_patient.name,
                queryset[0].invoice_number,
                queryset[0].invoice_date.strftime('%d-%m-%Y'))
        elif hasattr(queryset[0], 'patient'):
            _file_name = '-'.join([a.invoice_number for a in queryset.order_by("invoice_number")])
            response['Content-Disposition'] = 'attachment; filename="invoice-%s-%s-%s.pdf"' % (queryset[0].patient.name,
                                                                                               queryset[
                                                                                                   0].invoice_number,
                                                                                               queryset[
                                                                                                   0].invoice_date.strftime(
                                                                                                   '%d-%m-%Y'))

    elements = []
    if attach_to_email:
        io_buffer = BytesIO()
        doc = SimpleDocTemplate(io_buffer, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
        _payment_ref = "PR-MX-%s" % _file_name.replace(" ", "")[:10]
    else:
        doc = SimpleDocTemplate(response, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
        _payment_ref = "PR-%s" % _file_name.replace(" ", "")[:10]

    recapitulatif_data = []
    _recap_dates = []
    for qs in queryset.order_by("invoice_number"):
        _recap_dates.append(qs.invoice_date)
        dd = [qs.prestations.all().order_by("date", "carecode__name")[i:i + 20] for i in
              range(0, len(qs.prestations.all()), 20)]
        for _prestations in dd:
            _inv = qs.invoice_number + (
                ("" + str(dd.index(_prestations) + 1) + qs.invoice_date.strftime('%m%Y')) if len(dd) > 1 else "")
            _result = _build_invoices(_prestations,
                                      _inv,
                                      qs.invoice_date,
                                      qs.medical_prescription,
                                      qs.accident_id,
                                      qs.accident_date,
                                      qs.invoice_send_date,
                                      qs.patient)

            elements.extend(_result["elements"])
            recapitulatif_data.append((_result["invoice_number"], _result["patient_name"], _result["invoice_amount"]))
    if len(_recap_dates) > 0:
        _recap_date = _recap_dates[-1].strftime('%d-%m-%Y')
    else:
        _recap_date = now().date().strftime('%d-%m-%Y')
    elements.extend(_build_recap(_recap_date, _payment_ref, recapitulatif_data))
    doc.build(elements)

    if attach_to_email:
        subject = "Votre Facture %s" % _file_name
        message = "Bonjour, \nVeuillez trouver ci-joint la facture en pièce jointe. \nCordialement \n -- \n%s \n%s " \
                  "%s\n%s\n%s" % (config.NURSE_NAME, config.NURSE_ADDRESS, config.NURSE_ZIP_CODE_CITY,
                                  config.NURSE_PHONE_NUMBER, config.MAIN_BANK_ACCOUNT)
        emails = [qs.patient.email_address]
        mail = EmailMessage(subject, message, settings.EMAIL_HOST_USER, emails)
        mail.attach("%s.pdf" % _payment_ref, io_buffer.getvalue(), 'application/pdf')

        try:
            mail.send(fail_silently=False)
            return True
        except:
            return False
        finally:
            io_buffer.close()
    return response


def _build_invoices(prestations, invoice_number, invoice_date, prescription_date, accident_id, accident_date,
                    invoice_send_date, patient):
    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
    elements = []
    i = 0
    data = []
    patientSocNumber = '';
    patientNameAndFirstName = '';
    patientName = '';
    patientFirstName = '';
    patientAddress = ''

    data.append(('Num. titre', 'Prestation', 'Date', 'Heure', 'Nombre', 'Brut', 'P. CNS', 'P. Pers', 'Executant'))
    pytz_luxembourg = pytz.timezone("Europe/Luxembourg")
    for presta in prestations:
        i += 1
        patientSocNumber = patient.code_sn
        patientNameAndFirstName = patient
        patientName = patient.name
        patientFirstName = patient.first_name
        patientAddress = patient.address
        patientZipCode = patient.zipcode
        patientCity = patient.city
        data.append((i, presta.carecode.code,
                     (pytz_luxembourg.normalize(presta.date)).strftime('%d/%m/%Y'),
                     (pytz_luxembourg.normalize(presta.date)).strftime('%H:%M'),
                     presta.quantity,
                     presta.carecode.gross_amount(presta.date) * presta.quantity,
                     presta.carecode.net_amount(presta.date,
                                                patient.is_private,
                                                patient.participation_statutaire
                                                and patient.age > 18) * presta.quantity,
                     "%10.2f" % ((decimal.Decimal(presta.carecode.gross_amount(presta.date))
                                  - decimal.Decimal(presta.carecode.net_amount(presta.date,
                                                                               patient.is_private,
                                                                               patient.participation_statutaire and patient.age > 18))) * decimal.Decimal(
                         presta.quantity)),
                     presta.employee))

    for x in range(len(data), 22):
        data.append((x, '', '', '', '', '', '', '', ''))

    newData = []
    for y in range(0, len(data) - 1):
        newData.append(data[y])
        if (y % 10 == 0 and y != 0):
            _qty_sum = _compute_sum(data[y - 9:y + 1], 4)
            _gross_sum = _compute_sum(data[y - 9:y + 1], 5)
            _net_sum = _compute_sum(data[y - 9:y + 1], 6)
            _part_sum = _compute_sum(data[y - 9:y + 1], 7)
            newData.append(('', '', '', 'Sous-Total', _qty_sum, _gross_sum, _net_sum, _part_sum, ''))
    _total_facture = _compute_sum(data[1:], 7)
    newData.append((
        '', '', '', 'Total', _compute_sum(data[1:], 4), _compute_sum(data[1:], 5), _compute_sum(data[1:], 6),
        _compute_sum(data[1:], 7), ''))

    headerData = [['IDENTIFICATION DU FOURNISSEUR DE SOINS DE SANTE\n'
                   + "{0}\n{1}\n{2}\n{3}".format(config.NURSE_NAME, config.NURSE_ADDRESS, config.NURSE_ZIP_CODE_CITY,
                                                 config.NURSE_PHONE_NUMBER),
                   'CODE DU FOURNISSEUR DE SOINS DE SANTE\n{0}'.format(config.MAIN_NURSE_CODE)
                   ],
                  [u'Matricule patient: %s' % patientSocNumber.strip() + "\n"
                   + u'Nom et Prénom du patient: %s' % patientNameAndFirstName,
                   u'Nom: %s' % patientName.strip() + '\n'
                   + u'Prénom: %s' % patientFirstName.strip() + '\n'
                   + u'Rue: %s' % patientAddress.strip() + '\n'
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

    table = Table(newData, 9 * [2 * cm], 24 * [0.5 * cm])
    table.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                               ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('ALIGN', (0, -1), (-6, -1), 'RIGHT'),
                               ('INNERGRID', (0, -1), (-6, -1), 0, colors.white),
                               ('ALIGN', (0, -2), (-6, -2), 'RIGHT'),
                               ('INNERGRID', (0, -2), (-6, -2), 0, colors.white),
                               ('FONTSIZE', (0, 0), (-1, -1), 7),
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

    elements.append(PageBreak())

    return {"elements": elements
        , "invoice_number": invoice_number
        , "patient_name": patientName + " " + patientFirstName
        , "invoice_amount": newData[23][5]}


pdf_private_invoice.short_description = _("Private Invoice")


def _compute_sum(data, position):
    sum = 0
    for x in data:
        if x[position] != "":
            sum += decimal.Decimal(x[position])
    return round(sum, 2)


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
    _infos_iban = Table([[u"Lors du virement, veuillez indiquer la référence suivante: %s " % _recap_ref]], [10 * cm],
                        1 * [0.5 * cm], hAlign='LEFT')
    _date_infos = Table([["Date facture : %s " % _recap_date]], [10 * cm], 1 * [0.5 * cm], hAlign='LEFT')

    elements.append(_date_infos)
    elements.append(Spacer(1, 18))
    elements.append(_infos_iban)
    elements.append(Spacer(1, 18))
    _total_a_payer = Table([[u"Total à payer:", "%10.2f Euros" % total]], [10 * cm, 5 * cm], 1 * [0.5 * cm],
                           hAlign='LEFT')
    elements.append(_total_a_payer)
    elements.append(Spacer(1, 18))

    _infos_iban = Table([[u"Numéro IBAN: %s" % config.MAIN_BANK_ACCOUNT]], [10 * cm], 1 * [0.5 * cm], hAlign='LEFT')
    elements.append(_infos_iban)

    return elements
