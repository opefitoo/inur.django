# -*- coding: utf-8 -*-
import decimal
import os
from zoneinfo import ZoneInfo

from constance import config
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus.flowables import Spacer, PageBreak, Image
from reportlab.platypus.para import Paragraph
from reportlab.platypus.tables import Table, TableStyle


def get_doc_elements(queryset, med_p=False, with_verification_page=False):
    elements = []
    summary_data = []
    already_added_images = []
    copies_of_medical_prescriptions = []
    invoicing_details = None
    for qs in queryset.order_by("invoice_number"):
        if invoicing_details is None:
            invoicing_details = qs.invoice_details
        elif invoicing_details != qs.invoice_details:
            raise Exception("Invoices must have the same invoicing details found %s and %s" % (
                invoicing_details, qs.invoice_details))
        dd = [qs.prestations.all().order_by("date", "carecode__name")[i:i + 20] for i in
              range(0, len(qs.prestations.all()), 20)]
        for _prestations in dd:
            _inv = qs.invoice_number + (
                ("" + str(dd.index(_prestations) + 1) + qs.invoice_date.strftime('%m%Y')) if len(dd) > 1 else "")
            _result = _build_invoices(_prestations,
                                      _inv,
                                      qs.invoice_date,
                                      qs.accident_id,
                                      qs.accident_date,
                                      qs.invoice_details)

            elements.extend(_result["elements"])
            summary_data.append((_result["invoice_number"], _result["patient_name"], _result["invoice_amount"],
                                 _result["patient_cns_number"], _result["number_of_lines"]))
            elements.append(PageBreak())
            if med_p:
                if qs.get_all_medical_prescriptions().exists():
                    all_prescriptions = qs.get_all_medical_prescriptions().all()
                    for prescription in all_prescriptions:
                        try:
                            # print(prescription.medical_prescription.file_upload.file.name)
                            if prescription.medical_prescription.date.year == qs.invoice_date.year and \
                                    prescription.medical_prescription.date.month == qs.invoice_date.month:
                                elements.append(
                                    Paragraph(u"Ajouter ordonnance ORIGINALE %s" % prescription.medical_prescription,
                                              ParagraphStyle(name="Normal", alignment=TA_LEFT, fontSize=14)))
                                elements.append(Image(prescription.medical_prescription.thumbnail_img,
                                                      width=234.94,
                                                      height=389.595))
                                already_added_images.append(prescription.medical_prescription.file_upload.file.name)
                            elif prescription.medical_prescription.date.year != qs.invoice_date.year or prescription.medical_prescription.date.month != qs.invoice_date.month:
                                elements.append(
                                    Paragraph(u"Ajouter COPIE ordonnance  %s" % prescription.medical_prescription,
                                              ParagraphStyle(name="Normal", alignment=TA_LEFT, fontSize=14)))
                                elements.append(Image(prescription.medical_prescription.thumbnail_img,
                                                      width=234.94,
                                                      height=389.595))
                                already_added_images.append(prescription.medical_prescription.file_upload.file.name)
                                if prescription.medical_prescription.file_upload not in copies_of_medical_prescriptions:
                                    copies_of_medical_prescriptions.append(
                                        prescription.medical_prescription.file_upload)
                        except (FileNotFoundError,ValueError) as ex:
                            print(ex)
                            elements.append(
                                Paragraph(u"Fichier ordonnance cassé %s  %s%s " % (prescription.medical_prescription,
                                                                                   config.ROOT_URL,
                                                                                   prescription.medical_prescription.get_admin_url()),
                                          ParagraphStyle(name="Normal", alignment=TA_LEFT, fontSize=9,
                                                         textColor=colors.red)))
                        elements.append(PageBreak())

    recap_data = _build_recap(summary_data)
    elements.extend(recap_data[0])
    elements.append(PageBreak())
    if with_verification_page:
        verification_data = _build_verification_page(summary_data)
        elements.extend(verification_data[0])
        elements.append(PageBreak())
    elements.extend(_build_final_page(recap_data[1], recap_data[2], invoicing_details))

    return elements, copies_of_medical_prescriptions


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


def _build_verification_page(recaps):
    elements = []
    data = []
    i = 0
    data.append(("No d'ordre", u"Note no°", u"Nom et prénom", "Montant", "Num. cns", "Nb. lignes"))
    total = 0.0
    for recap in recaps:
        i += 1
        data.append((i, recap[0], recap[1], recap[2], recap[3], recap[4]))
        total = decimal.Decimal(total) + decimal.Decimal(recap[2])
    data.append(("", "", u"à reporter", round(total, 2), ""))

    table = Table(data, [2 * cm, 2 * cm, 6 * cm, 3 * cm, 3 * cm, 2 * cm], (i + 2) * [0.75 * cm])
    table.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                               ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('FONTSIZE', (0, 0), (-1, -1), 9),
                               ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                               ]))
    elements.append(table)
    return elements, total, i


def _build_final_page(total, order_number, invoicing_details):
    elements = []
    data = [["RELEVE DES NOTES D’HONORAIRES DES"],
            ["ACTES ET SERVICES DES INFIRMIERS"]]
    table = Table(data, [10 * cm], [0.75 * cm, 0.75 * cm])
    table.setStyle(TableStyle([('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                               ('INNERGRID', (0, 0), (-1, -1), 0, colors.white),
                               ('FONTSIZE', (0, 0), (-1, -1), 12),
                               ('BOX', (0, 0), (-1, -1), 1.25, colors.black),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                               ]))
    elements.append(table)
    elements.append(Spacer(1, 18))
    data2 = [
        [u"Identification du fournisseur de", invoicing_details.name, "", u"réservé à l’union des caisses de maladie"],
        [u"soins de santé", "", "", ""],
        [u"Coordonnées bancaires :", invoicing_details.bank_account, "", ""],
        ["Code: ", invoicing_details.provider_code, "", ""]]
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
    elements.append(Paragraph(
        u"Récapitulation des notes d’honoraires du chef de la fourniture de soins de santé dispensés aux personnes protégées relevant de l’assurance maladie / assurance accidents ou de l’assurance dépendance.",
        styles['Justify']))
    elements.append(Spacer(2, 20))
    elements.append(
        Paragraph(u"Pendant la période du :.................................. au :..................................",
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
    data4 = [[
        u"Montant total des honoraires à charge de\nl’organisme assureur (montant net cf. zone 14) du\nmém. d’honoraires):",
        "%.2f EUR" % round(total, 2)]]
    table4 = Table(data4, [9 * cm, 8 * cm], [1.25 * cm])
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


def _build_invoices(prestations, invoice_number, invoice_date, accident_id, accident_date, invoicing_details):
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
    patient_cns_number = ''
    number_of_lines = 0

    data.append(('Num. titre', 'Prestation', 'Date', 'Nombre', 'Brut', 'Net', 'Heure', 'P. Pers', 'Executant'))
    for presta in prestations:
        patient = presta.invoice_item.patient
        patientSocNumber = patient.code_sn
        patientNameAndFirstName = patient
        patientName = patient.name
        patientFirstName = patient.first_name
        patientAddress = patient.address
        patientZipCode = patient.zipcode
        patientCity = patient.city
        patient_cns_number = patient.code_sn
        if presta.carecode.reimbursed:
            i += 1
            data.append((i, presta.carecode.code,
                         (presta.date.astimezone(ZoneInfo("Europe/Luxembourg"))).strftime('%d/%m/%Y'),
                         '1',
                         # keep only 2 decimals
                         round(presta.carecode.gross_amount(presta.date), 2),
                         round(presta.carecode.net_amount(presta.date, patient.is_private,
                                                          (patient.participation_statutaire
                                                           and patient.age > 18)), 2),
                         (presta.date.astimezone(ZoneInfo("Europe/Luxembourg"))).strftime('%H:%M'),
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
                   + "{0}\n{1}\n{2}\n{3}".format(invoicing_details.name, invoicing_details.address,
                                                 invoicing_details.zipcode_city,
                                                 invoicing_details.phone_number),
                   'CODE DU FOURNISSEUR DE SOINS DE SANTE\n{0}'.format(invoicing_details.provider_code),
                   ],
                  [u'Matricule patient: %s' % patientSocNumber.strip() + "\n"
                   + u'Nom et Prénom du patient: %s' % patientNameAndFirstName,
                   u'Nom: %s' % patientName.strip() + '\n'
                   + u'Pénom: %s' % patientFirstName.strip() + '\n'
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
            "patient_name": patientName + " " + patientFirstName, "invoice_amount": newData[23][5],
            "patient_cns_number": patient_cns_number, "number_of_lines": i}


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

    # @staticmethod
    # def get_inmemory_pdf(batch):
    #     io_buffer = BytesIO()
    #     doc = SimpleDocTemplate(io_buffer, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
    #     elements = get_doc_elements(batch.invoice_items)
    #     doc.build(elements)
    #
    #     f = io_buffer.getvalue()
    #     in_memory_file = InMemoryUploadedFile(io_buffer,
    #                                           field_name=None,
    #                                           name=InvoiceItemBatchPdf.get_filename(batch=batch),
    #                                           content_type="application/pdf",
    #                                           size=sys.getsizeof(f),
    #                                           charset=None)
    #
    #     return in_memory_file
