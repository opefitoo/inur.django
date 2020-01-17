# -*- coding: utf-8 -*-
import sys
import os

from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus.flowables import Spacer, PageBreak, Image
from reportlab.platypus.para import Paragraph
from reportlab.platypus.tables import Table, TableStyle
from reportlab.platypus.doctemplate import SimpleDocTemplate
import pytz
from django.utils.encoding import smart_text
import decimal
from constance import config


def get_doc_elements(queryset):
    elements = []
    recapitulatif_data = []

    for qs in queryset.order_by("invoice_number"):
        dd = [qs.prestations.all().order_by("date", "carecode__name")[i:i + 20] for i in
              range(0, len(qs.prestations.all()), 20)]
        for _prestations in dd:
            _inv = qs.invoice_number + (
                ("" + str(dd.index(_prestations) + 1) + qs.invoice_date.strftime('%m%Y')) if len(dd) > 1 else "")
            _result = _build_invoices(_prestations,
                                      _inv,
                                      qs.invoice_date,
                                      qs.accident_id,
                                      qs.accident_date)

            elements.extend(_result["elements"])
            recapitulatif_data.append((_result["invoice_number"], _result["patient_name"], _result["invoice_amount"]))
            elements.append(PageBreak())
            if qs.medical_prescription and qs.medical_prescription.file:
                elements.append(Image(qs.medical_prescription.file, width=469.88, height=773.19))
                elements.append(PageBreak())
    recap_data = _build_recap(recapitulatif_data)
    elements.extend(recap_data[0])
    elements.append(PageBreak())
    elements.extend(_build_final_page(recap_data[1], recap_data[2]))

    return elements


def _build_recap(recaps):
    elements = []
    data = []
    i = 0
    data.append(("No d'ordre", u"Note no°", u"Nom et prénom", "Montant", u"réservé à la caisse"))
    total = 0.0
    for recap in recaps:
        i += 1
        data.append((i, recap[0], recap[1], recap[2], ""))
        total = decimal.Decimal(total) + decimal.Decimal(recap[2])
    data.append(("", "", u"à reporter", round(total, 2), ""))

    table = Table(data, [2 * cm, 3 * cm, 7 * cm, 3 * cm, 3 * cm], (i + 2) * [0.75 * cm])
    table.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                               ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('FONTSIZE', (0, 0), (-1, -1), 9),
                               ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                               ]))
    elements.append(table)
    return elements, total, i


def _build_final_page(total, order_number):
    elements = []
    data = [["RELEVE DES NOTES D’HONORAIRES DES"],
            ["ACTES ET SERVICES DES INFIRMIERS"]]
    table = Table(data, [10 * cm], [0.75 * cm, 0.75*cm])
    table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                               ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
                               ('FONTSIZE', (0, 0), (-1, -1),  12),
                               ('BOX', (0, 0), (-1, -1), 1.25, colors.black),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ]))
    elements.append(table)
    elements.append(Spacer(1, 18))
    data2 = [[u"Identification du fournisseur de", config.NURSE_NAME, "", u"réservé à l’union des caisses de maladie"],
             [u"soins de santé",  "", "", ""],
             [u"Coordonnées bancaires :", config.MAIN_BANK_ACCOUNT, "", ""],
             ["Code: ", config.MAIN_NURSE_CODE, "", ""]]
    table2 = Table(data2, [5 * cm, 3 * cm, 3 * cm, 7 * cm], [1.25 * cm, 0.5 * cm, 1.25 * cm, 1.25 * cm])
    table2.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                                ('ALIGN', (3, 0), (3, 0), 'CENTER'),
                                ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
                                ('SPAN', (1, 2), (2, 2)),
                                ('FONTSIZE', (0, 0), (-1, -1), 8),
                                ('BOX', (3, 0), (3, 3), 0.25, colors.black),
                                ('BOX', (3, 0), (3, 1), 0.25, colors.black),
                                ('BOX', (1, 3), (1, 3), 1, colors.black)]))
    elements.append(table2)
    elements.append(Spacer(1, 20))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Justify', alignment=TA_JUSTIFY))
    elements.append(Paragraph(u"Récapitulation des notes d’honoraires du chef de la fourniture de soins de santé dispensés aux personnes protégées relevant de l’assurance maladie / assurance accidents ou de l’assurance dépendance.",
                              styles['Justify']))
    elements.append(Spacer(2, 20))
    elements.append(Paragraph(u"Pendant la période du :.................................. au :..................................",
                              styles['Justify']))
    data3 = [["Nombre des mémoires d’honoraires ou\nd’enregistrements du support informatique:",
              order_number]]
    table3 = Table(data3, [9 * cm, 8 * cm], [1.25 * cm])
    table3.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'LEFT'),
                                ('ALIGN', (-1, -1), (-1, -1), 'CENTER'),
                                ('VALIGN', (-1, -1), (-1, -1), 'MIDDLE'),
                               ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
                               ('FONTSIZE', (0, 0), (-1, -1), 9),
                               ('BOX', (1, 0), (-1, -1), 1.25, colors.black)]))
    elements.append(Spacer(2, 20))
    elements.append(table3)
    elements.append(Spacer(2, 20))
    data4 = [[u"Montant total des honoraires à charge de\nl’organisme assureur (montant net cf. zone 14) du\nmém. d’honoraires):",
              "%.2f EUR" %round(total, 2)]]
    table4 = Table(data4    , [9 * cm, 8 * cm], [1.25 * cm])
    table4.setStyle(TableStyle([('ALIGN', (0, 0), (0, 0), 'LEFT'),
                                ('ALIGN', (-1, -1), (-1, -1), 'CENTER'),
                                ('VALIGN', (-1, -1), (-1, -1), 'MIDDLE'),
                                ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
                                ('FONTSIZE', (0, 0), (-1, -1), 9),
                                ('BOX', (1, 0), (-1, -1), 1.25, colors.black)]))
    elements.append(table4)
    elements.append(Spacer(40, 60))
    styles.add(ParagraphStyle(name='Left', alignment=TA_LEFT))
    elements.append(Paragraph(
        u"Certifié sincère et véritable, mais non encore acquitté: ________________ ,le ______________________",
        styles['Left']))
    return elements


def _build_invoices(prestations, invoice_number, invoice_date, accident_id, accident_date):
    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
    # import pydevd; pydevd.settrace()
    elements = []
    i = 0
    data = []
    patientSocNumber = ''
    patientNameAndFirstName = ''
    patientName = ''
    patientFirstName = ''
    patientAddress = ''

    data.append(('Num. titre', 'Prestation', 'Date', 'Nombre', 'Brut', 'Net', 'Heure', 'P. Pers', 'Executant'))
    pytz_luxembourg = pytz.timezone("Europe/Luxembourg")
    for presta in prestations:
        patient = presta.invoice_item.patient
        patientSocNumber = patient.code_sn
        patientNameAndFirstName = patient
        patientName = patient.name
        patientFirstName = patient.first_name
        patientAddress = patient.address
        patientZipCode = patient.zipcode
        patientCity = patient.city
        if presta.carecode.reimbursed:
            i += 1
            data.append((i, presta.carecode.code,
                         (pytz_luxembourg.normalize(presta.date)).strftime('%d/%m/%Y'),
                         '1',
                         presta.carecode.gross_amount(presta.date),
                         presta.carecode.net_amount(presta.date, patient.is_private, (patient.participation_statutaire
                                                                                      and patient.age > 18)),
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

    headerData = [['IDENTIFICATION DU FOURNISSEUR DE SOINS DE SANTE\n'
                   + "{0}\n{1}\n{2}\n{3}".format(config.NURSE_NAME, config.NURSE_ADDRESS, config.NURSE_ZIP_CODE_CITY,
                                                 config.NURSE_PHONE_NUMBER),
                   'CODE DU FOURNISSEUR DE SOINS DE SANTE\n{0}'.format(config.MAIN_NURSE_CODE)
                   ],
                  [u'Matricule patient: %s' % smart_text(patientSocNumber.strip()) + "\n"
                   + u'Nom et Pr' + smart_text("e") + u'nom du patient: %s' % smart_text(patientNameAndFirstName),
                   u'Nom: %s' % smart_text(patientName.strip()) + '\n'
                   + u'Pr' + smart_text(u"é") + u'nom: %s' % smart_text(patientFirstName.strip()) + '\n'
                   + u'Rue: %s' % patientAddress.strip() + '\n'
                   + u'Code postal: %s' % smart_text(patientZipCode.strip()) + '\n'
                   + u'Ville: %s' % smart_text(patientCity.strip())],
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
                               ('FONTSIZE', (0, 0), (-1, -1), 8),
                               ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                               ]))

    elements.append(headerTable)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    elements.append(Spacer(1, 18))
    elements.append(
        Paragraph(u"Mémoire d'Honoraires Num. %s en date du : %s" % (invoice_number, invoice_date), styles['Center']))
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

    _pouracquit_signature = Table([["Pour acquit, le:", "Signature et cachet"]], [10 * cm, 10 * cm], 1 * [0.5 * cm],
                                  hAlign='LEFT')

    elements.append(_pouracquit_signature)
    return {"elements": elements, "invoice_number": invoice_number,
            "patient_name": patientName + " " + patientFirstName, "invoice_amount": newData[23][5]}


def _compute_sum(data, position):
    sum = 0
    for x in data:
        if x[position] != "":
            sum += x[position]
    return sum


class InvoiceItemBatchPdf:
    @staticmethod
    def get_filename(batch):
        prefix = 'InvoiceItemBatch'

        return '%s %s.pdf' % (prefix, str(batch))

    @staticmethod
    def get_path(batch):
        from invoices.models import gd_storage
        filename = InvoiceItemBatchPdf.get_filename(batch=batch)

        return os.path.join(gd_storage.INVOICEITEM_BATCH_FOLDER, filename)

    @staticmethod
    def get_inmemory_pdf(batch):
        io_buffer = BytesIO()
        doc = SimpleDocTemplate(io_buffer, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
        elements = get_doc_elements(batch.invoice_items)
        doc.build(elements)

        f = io_buffer.getvalue()
        in_memory_file = InMemoryUploadedFile(io_buffer,
                                              field_name=None,
                                              name=InvoiceItemBatchPdf.get_filename(batch=batch),
                                              content_type="application/pdf",
                                              size=sys.getsizeof(f),
                                              charset=None)

        return in_memory_file
