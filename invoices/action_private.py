# -*- coding: utf-8 -*-
import decimal
from io import BytesIO
from zoneinfo import ZoneInfo

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
from reportlab.platypus.flowables import Spacer, PageBreak, Image
from reportlab.platypus.para import Paragraph
from reportlab.platypus.tables import Table, TableStyle

from invoices import settings
from invoices.models import InvoiceItemEmailLog
from invoices.modelspackage import InvoicingDetails
from invoices.settings import BASE_DIR
from invoices.xero.exceptions import XeroTokenRefreshError
from invoices.xero.invoice import create_xero_invoice


class Footer:
    def __init__(self, legal_mention):
        self.legal_mention = legal_mention

    def __call__(self, canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 7)
        canvas.drawString(1 * cm, 0.8 * cm, self.legal_mention)

        # Draw logo
        logo = 'invoices/static/images/Logo_SUR_quadri_transparent_pour_copas.png'
        # resize image but keep ratio
        img = Image(logo)
        img.drawHeight = 1.75 * cm * img.drawHeight / img.drawWidth
        img.drawWidth = 1.75 * cm
        img.wrapOn(canvas, doc.width, doc.topMargin)
        # draw on right, vertical-align middle
        img.drawOn(canvas, doc.width - 0.25 * cm, (doc.bottomMargin - img.drawHeight) / 2 + 1.5 * cm)
        canvas.restoreState()


def pdf_private_invoice(modeladmin, request, queryset, attach_to_email=False, only_to_xero_or_any_accounting_system=False):
    # Create the HttpResponse object with the appropriate PDF headers.
    invoicing_details = None
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
    payment_reference_hash = ""
    # if only one invoice in the queryset, use the invoice number as reference
    if len(queryset) == 1:
        _payment_ref = "PP%s" % queryset[0].invoice_number
    else:
        # if multiple invoices in the queryset, use the hash of the invoice numbers as reference
        for qs in queryset.order_by("invoice_number"):
            payment_reference_hash += str(qs.invoice_number)
        _payment_ref = "PP%s" % str(abs(hash(payment_reference_hash)))[:6]
    if attach_to_email:
        io_buffer = BytesIO()
        doc = SimpleDocTemplate(io_buffer, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
        _payment_ref = "MX-%s" % _payment_ref
    else:
        doc = SimpleDocTemplate(response, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
    # build a string with invoicing details with the name of the company, zipcode address, phone number and bank account
    recapitulatif_data = []
    _recap_dates = []
    for qs in queryset.order_by("invoice_number"):
        if invoicing_details is None:
            invoicing_details = qs.invoice_details
        elif invoicing_details != qs.invoice_details:
            raise Exception("Invoices must have the same invoicing details found %s and %s" % (
                invoicing_details, qs.invoice_details))
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
                                      patient=qs.patient,
                                      invoice_paid=qs.invoice_paid,
                                      invoicing_details=invoicing_details, )

            elements.extend(_result["elements"])
            if not qs.invoice_paid:
                recapitulatif_data.append(
                    (_result["invoice_number"], _result["patient_name"], _result["invoice_amount"]))
    if len(_recap_dates) > 0:
        _recap_date = _recap_dates[-1].strftime('%d-%m-%Y')
    else:
        _recap_date = now().date().strftime('%d-%m-%Y')
    if len(recapitulatif_data) > 0:
        elements.extend(_build_recap(_recap_date, _payment_ref, recapitulatif_data, invoicing_details))
    # pass parameter to footer
    # build a string with invoicing details with the name of the company, zipcode address, phone number and bank account
    if invoicing_details is None:
        invoicing_details = InvoicingDetails.objects.get(default_invoicing=True)
    # if both invoicing_details af and aa are empty, do not display them
    if invoicing_details.af == "" and invoicing_details.rc == "":
        legal_mention = f"{invoicing_details.name} {invoicing_details.address} {invoicing_details.zipcode_city} " \
                        f"tel:{invoicing_details.phone_number} iban:{invoicing_details.bank_account}"
    else:
        legal_mention = f"{invoicing_details.name} {invoicing_details.address} {invoicing_details.zipcode_city} " \
                        f"tel:{invoicing_details.phone_number} iban:{invoicing_details.bank_account} RC:{invoicing_details.rc} Agrément:{invoicing_details.af}"
    footer2 = Footer(legal_mention)

    doc.build(elements, onFirstPage=footer2, onLaterPages=footer2)

    if attach_to_email:
        if queryset.order_by("invoice_number").count() > 1:
            raise Exception("Cannot attach multiple invoices to email")
        subject = "Votre Facture %s" % _file_name
        message = "Bonjour, \nVeuillez trouver ci-joint la facture en pièce jointe.\nSi ce courrier a croisé votre paiement, veuillez considérer ce message (rappel) comme nul et non avenu.\nCordialement \n -- \n%s \n%s " \
                  "%s\n%s\n%s" % (invoicing_details.name, invoicing_details.address, invoicing_details.zipcode_city,
                                  invoicing_details.phone_number, invoicing_details.bank_account)
        if only_to_xero_or_any_accounting_system:
            try:
                create_xero_invoice(queryset[0], _result["invoice_amount"], io_buffer.getvalue())
            except XeroTokenRefreshError as e:
                return redirect('xero-auth')
        else:
            emails = [qs.patient.email_address]
            if config.CC_EMAIL_SENT:
                emails += config.CC_EMAIL_SENT.split(",")
                mail = EmailMessage(subject, message, settings.EMAIL_HOST_USER, emails)
                mail.attach("%s.pdf" % _payment_ref, io_buffer.getvalue(), 'application/pdf')

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
                    invoice_send_date, patient, invoice_paid=False, invoicing_details=None):
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
    zoneinfo = ZoneInfo("Europe/Luxembourg")
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
                     (presta.date.astimezone(zoneinfo)).strftime('%d/%m/%Y'),
                     (presta.date.astimezone(zoneinfo)).strftime('%H:%M'),
                     presta.quantity,
                     round(presta.carecode.gross_amount(presta.date), 2) * presta.quantity,
                     presta.carecode.net_amount(presta.date,
                                                patient.is_private,
                                                patient.participation_statutaire
                                                and patient.age > 18) * presta.quantity,
                     "%10.2f" % ((decimal.Decimal(presta.carecode.gross_amount(presta.date))
                                  - decimal.Decimal(presta.carecode.net_amount(presta.date,
                                                                               patient.is_private,
                                                                               patient.participation_statutaire and patient.age > 18))) * decimal.Decimal(
                         presta.quantity)),
                     presta.employee.provider_code))

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
                   + "{0}\n{1}\n{2}\n{3}".format(invoicing_details.name, invoicing_details.address,
                                                 invoicing_details.zipcode_city, invoicing_details.phone_number),
                   'CODE DU FOURNISSEUR DE SOINS DE SANTE\n{0}'.format(invoicing_details.provider_code),
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
    if prescription_date is not None:
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
    _invoice_paid_stample = Table([["", "Facture Acquitée", ""]], [1 * cm, 4 * cm], 1 * [0.5 * cm], hAlign='CENTER')
    _invoice_paid_stample.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'RIGHT'),
                                               ('INNERGRID', (0, 0), (0, 0), 1, colors.red),
                                               ('FONTSIZE', (0, 0), (-1, -1), 9),
                                               ('BOX', (0, 0), (1, 1), 1, colors.red),
                                               ('TEXTCOLOR', (0, 0), (1, 1), colors.red),
                                               ('SPAN', (1, 1), (3, 2)),
                                               ]))
    elements.append(Spacer(1, 18))
    elements.append(_2derniers_cases)
    elements.append(Spacer(1, 18))
    if invoice_paid:
        elements.append(_invoice_paid_stample)
        signature_img = Image(BASE_DIR + "/static/images/signature_regine_transparent.png")
        signature_img.drawHeight = 2 * cm
        signature_img.drawWidth = 2 * cm
        elements.append(signature_img)
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


def _build_recap(_recap_date, _recap_ref, recaps, invoicing_details):
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

    _infos_iban = Table([[u"Numéro IBAN: %s" % invoicing_details.bank_account]], [10 * cm], 1 * [0.5 * cm],
                        hAlign='LEFT')
    elements.append(_infos_iban)

    return elements
