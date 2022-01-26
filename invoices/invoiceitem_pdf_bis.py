# -*- coding: utf-8 -*-
import sys
import os

from io import BytesIO

from constance import config
from django.core.files.uploadedfile import InMemoryUploadedFile
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus.flowables import Spacer, PageBreak
from reportlab.platypus.para import Paragraph
from reportlab.platypus.tables import Table, TableStyle
from reportlab.platypus.doctemplate import SimpleDocTemplate
import pytz
import decimal


def get_doc_elements(queryset, payment_ref):
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
    elements.extend(_build_recap(recapitulatif_data, payment_ref))

    return elements


def _build_recap(recaps, payment_ref):
    elements = []
    data = []
    i = 0
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    elements.append(Spacer(3, 18))
    elements.append(
        Paragraph(u"Récapitulatif des notes", styles['Center']))
    elements.append(Spacer(3, 18))

    data.append(("No d'ordre", u"Note no°", u"Nom et prénom", "Montant"))
    total = 0.0
    for recap in recaps:
        i += 1
        data.append((i, recap[0], recap[1], recap[2]))
        total = decimal.Decimal(total) + decimal.Decimal(recap[2])
    data.append(("", "", u"Total", round(total, 2)))

    table = Table(data, [2 * cm, 3 * cm, 7 * cm, 3 * cm, 3 * cm])
    table.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                               ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('FONTSIZE', (0, 0), (-1, -1), 9),
                               ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                               ]))
    elements.append(table)

    elements.append(Spacer(3, 18))

    _intro = Table([[
                        u"Veuillez trouver ci-joint le récapitulatif des notes ainsi que le montant total payer"]],
                   [10 * cm, 5 * cm], 1 * [0.5 * cm], hAlign='LEFT')
    elements.append(_intro)

    _total_a_payer = Table([["Total " + u"à" + " payer:", "%10.2f Euros" % total]], [10 * cm, 5 * cm], 1 * [0.5 * cm],
                           hAlign='LEFT')
    elements.append(_total_a_payer)
    elements.append(Spacer(1, 18))

    _infos_iban = Table([[u"Numéro IBAN: %s" % config.MAIN_BANK_ACCOUNT]], [10*cm], 1*[0.5*cm], hAlign='LEFT')
    elements.append(_infos_iban)

    elements.append(Spacer(1, 18))
    _infos_iban = Table([[u"Lors du virement, veuillez indiquer la référence: %s " % payment_ref.upper()]],
                        [10 * cm], 1 * [0.5 * cm], hAlign='LEFT')
    elements.append(_infos_iban)

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
                         presta.carecode.gross_amount(presta.date),
                         (pytz_luxembourg.normalize(presta.date)).strftime('%H:%M'),
                         "",
                         #TODO : replace with Global setting
                         "300744-44"))

    for x in range(len(data), 22):
        data.append((x, '', '', '', '', '', '', '', ''))

    newData = []
    for y in range(0, len(data) - 1):
        newData.append(data[y])
        if y % 10 == 0 and y != 0:
            _gross_sum = _compute_sum(data[y - 9:y + 1], 4)
            _net_sum = _compute_sum(data[y - 9:y + 1], 5)
            newData.append(('', '', '', 'Sous-Total', _gross_sum, _net_sum, '', '', ''))
    newData.append(('', '', '', 'Total', _compute_sum(data[1:], 4), _compute_sum(data[1:], 5), '', '', ''))
    _total_facture = _compute_sum(data[1:], 5)

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
    elements.append(Spacer(1, 18))
    _total_a_payer = Table([["Total facture:", "%10.2f Euros" % _total_facture]], [10 * cm, 5 * cm], 1 * [0.5 * cm],
                           hAlign='LEFT')
    elements.append(Spacer(1, 18))
    elements.append(_total_a_payer)
    elements.append(Spacer(1, 18))

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
