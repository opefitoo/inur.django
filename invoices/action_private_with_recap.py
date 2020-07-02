# -*- coding: utf-8 -*-
from constance import config
from django.http import HttpResponse
from django.utils.encoding import smart_text
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus.doctemplate import SimpleDocTemplate
from reportlab.platypus.flowables import Spacer, PageBreak
from reportlab.platypus.para import Paragraph
from reportlab.platypus.tables import Table, TableStyle
from django.utils.timezone import localtime, now
import decimal

def pdf_private_invoice_with_recap(modeladmin, request, queryset):
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    # Append invoice number and invoice date
    _payment_ref = ''
    _recap_date = ''
    if len(queryset) != 1:
        _file_name = '-'.join([a.invoice_number for a in queryset.order_by("invoice_number")])
        _payment_ref = _file_name.replace(" ", "")[:10]
        _recap_date = now().date().strftime('%d-%m-%Y')
        response['Content-Disposition'] = 'attachment; filename="invoice%s.pdf"' %(_file_name.replace(" ", "")[:150])
    else:
        _payment_ref = "PI.%s %s" % (queryset[0].invoice_number, queryset[0].invoice_date.strftime('%d.%m.%Y'))
        _recap_date = queryset[0].invoice_date.strftime('%d-%m-%Y')
        response['Content-Disposition'] = 'attachment; filename="invoice-%s-%s-%s.pdf"' %(queryset[0].private_patient.name,
                                                                                          queryset[0].invoice_number, 
                                                                                          queryset[0].invoice_date.strftime('%d-%m-%Y'))
    
    elements = []
    doc = SimpleDocTemplate(response, rightMargin=2*cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1*cm)
    
    recapitulatif_data = []

    for qs in queryset.order_by("invoice_number"):
        dd = [qs.prestations.all().order_by("date", "carecode__gross_amount")[i:i+20] for i in range(0, len(qs.prestations.all()), 20)]
        for _prestations in dd:
            _inv = qs.invoice_number + (("" + str(dd.index(_prestations) + 1) + qs.invoice_date.strftime('%m%Y')) if len(dd) > 1 else "")
            _result = _build_invoices(_prestations, 
                                      _inv, 
                                      qs.invoice_date,
                                      qs.medical_prescription_date, 
                                      qs.accident_id, 
                                      qs.accident_date )
                                      
            elements.extend(_result["elements"])
            recapitulatif_data.append((_result["invoice_number"], _result["patient_name"], _result["invoice_amount"]))
            elements.append(PageBreak())
    import datetime
    elements.extend(_build_recap( _recap_date, _payment_ref , recapitulatif_data))
    doc.build(elements)
    return response

def _build_invoices(prestations, invoice_number, invoice_date, prescription_date, accident_id, accident_date):
    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
    #import pydevd; pydevd.settrace()
    elements = []
    i = 0
    data = []
    patientSocNumber = '';
    patientNameAndFirstName = '';
    patientName = '';
    patientFirstName = '';
    patientAddress = ''

    data.append(('Num. titre', 'Prestation', 'Date', 'Nombre', 'Brut', 'Net', 'Heure', 'P. Pers','Executant'))
    for presta in prestations:
        i+=1
        patientSocNumber = presta.patient.code_sn
        patientNameAndFirstName = presta.patient
        patientName = presta.patient.name
        patient_first_name = presta.patient.first_name
        patient_address = presta.patient.address
        patientZipCode = presta.patient.zipcode
        patientCity = presta.patient.city
        data.append((i, presta.carecode.code, 
                     (presta.date).strftime('%d/%m/%Y'),
                     '1', 
                     presta.carecode.gross_amount, 
                     presta.net_amount, 
                     localtime(presta.date).strftime('%H:%M'),
                     "", 
                     "300744-44"))
    
    for x in range(len(data)  , 22):
        data.append((x, '', '', '', '', '', '', '',''))
            
    newData = []
    for y in range(0, len(data) -1) :
        newData.append(data[y])
        if(y % 10 == 0 and y != 0):
            _gross_sum = _compute_sum(data[y-9:y+1], 4)
            _net_sum = _compute_sum(data[y-9:y+1], 5)
            _part_sum = _compute_sum(data[y - 9:y + 1], 6)
            newData.append(('', '', '', 'Sous-Total', "%10.2f" % _gross_sum, "%10.2f" % _net_sum, "%10.2f" % _part_sum))
    _total_facture = _compute_sum(data[1:], 5)
    _participation_personnelle = decimal.Decimal(_compute_sum(data[1:], 4)) - decimal.Decimal(_total_facture)
    newData.append(('', '', '', 'Total', "%10.2f" % _compute_sum(data[1:], 4), "%10.2f" % _compute_sum(data[1:], 5), "%10.2f" % _compute_sum(data[1:], 6)))

    headerData = [['IDENTIFICATION DU FOURNISSEUR DE SOINS DE SANTE\n'
                   + "{0}\n{1}\n{2}\n{3}".format(config.NURSE_NAME,
                                                 config.NURSE_ADDRESS,
                                                 config.NURSE_ZIP_CODE_CITY,
                                                 config.NURSE_PHONE_NUMBER),
                   'CODE DU FOURNISSEUR DE SOINS DE SANTE\n{0}'.format(config.MAIN_NURSE_CODE)
                   ],
                  [u'Matricule patient: %s' % smart_text(patientSocNumber.strip()) + "\n"
                   + u'Nom et Prénom du patient: %s' % smart_text(patientNameAndFirstName),
                   u'Nom: %s' % smart_text(patientName.strip()) + '\n'
                   + u'Pr' + smart_text(u"é") + u'nom: %s' % smart_text(patient_first_name.strip()) + '\n'
                   + u'Rue: %s' % patient_address.strip() + '\n'
                   + u'Code postal: %s' % smart_text(patientZipCode.strip()) + '\n'
                   + u'Ville: %s' % smart_text(patientCity.strip())],
                  [u'Date accident: %s\n' % (accident_date if accident_date else "")
                   + u'Num. accident: %s' % (accident_id if accident_id else "")]]
    
    headerTable = Table(headerData, 2*[10*cm], [2.5*cm, 1*cm, 1.5*cm] )
    headerTable.setStyle(TableStyle([('ALIGN',(1,1),(-2,-2),'LEFT'),
                       ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                       ('FONTSIZE', (0,0), (-1,-1), 9),
                       ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                       ('SPAN', (1, 1) , (1,2)),
                       ]))
    
    
    table = Table(newData, 9*[2*cm], 24*[0.5*cm] )
    table.setStyle(TableStyle([('ALIGN',(1,1),(-2,-2),'LEFT'),
                       ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                       ('ALIGN',(0,-1), (-6,-1),'RIGHT'),
                       ('INNERGRID', (0,-1), (-6,-1), 0, colors.white),
                       ('ALIGN',(0,-2), (-6,-2),'RIGHT'),
                       ('INNERGRID', (0,-2), (-6,-2), 0, colors.white),
                       ('FONTSIZE', (0,0), (-1,-1), 7),
                       ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                       ]))

    elements.append(headerTable)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    elements.append(Spacer(1, 18))
    if(prescription_date is not None):
        elements.append(Paragraph(u"Mémoire d'Honoraires Num. %s en date du : %s Ordonnance du %s " %( invoice_number, invoice_date, prescription_date), styles['Heading4']))
    else:
        elements.append(Paragraph(u"Mémoire d'Honoraires Num. %s en date du : %s " %( invoice_number, invoice_date), styles['Heading4']))

    elements.append(Spacer(1, 18))

    elements.append(table)

    _2derniers_cases = Table([["", "Paiement Direct"]], [1*cm, 4*cm], 1*[0.5*cm], hAlign='LEFT' )
    _2derniers_cases.setStyle(TableStyle([('ALIGN',(1,1),(-2,-2),'RIGHT'),
                       ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                       ('FONTSIZE', (0,0), (-1,-1), 9),
                       ('BOX', (0,0), (0,0), 0.75, colors.black),
                       ('SPAN', (1, 1) , (1,2)),
                       ]))
    
    elements.append(Spacer(1, 18))
    
    elements.append(_2derniers_cases)
    _2derniers_cases = Table([["", "Tiers payant"]], [1*cm, 4*cm], 1*[0.5*cm], hAlign='LEFT' )
    _2derniers_cases.setStyle(TableStyle([('ALIGN',(1,1),(-2,-2),'RIGHT'),
                       ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                       ('FONTSIZE', (0,0), (-1,-1), 9),
                       ('BOX', (0,0), (0,0), 0.75, colors.black),
                       ('SPAN', (1, 1) , (1,2)),
                       ]))
    elements.append(Spacer(1, 18))
    elements.append(_2derniers_cases)
    elements.append(Spacer(1, 18))
    _total_a_payer = Table([["Total facture:",  "%10.2f Euros" % _total_facture ]], [10*cm, 5*cm], 1*[0.5*cm], hAlign='LEFT')
    elements.append(Spacer(1, 18))
    elements.append( _total_a_payer )
    elements.append(Spacer(1, 18))
    
    _pouracquit_signature = Table([["Pour acquit, le:", "Signature et cachet"]], [10*cm, 10*cm], 1*[0.5*cm], hAlign='LEFT')

    ## TODO: global setting replacement
    _infos_iban = Table([[u"Numéro IBAN: %s" % config.MAIN_BANK_ACCOUNT]], [10*cm], 1*[0.5*cm], hAlign='LEFT')
    elements.append(Spacer(1, 10))
    #elements.append(_infos_iban)
    if prescription_date is not None:
        _infos_iban = Table([["Lors du virement, veuillez indiquer la r"+ u"é" + "f"+ u"é"+ "rence: %s Ordonnance du %s " %(invoice_number,prescription_date)]], [10*cm], 1*[0.5*cm], hAlign='LEFT')
    else:
        _infos_iban = Table([["Lors du virement, veuillez indiquer la r"+ u"é" + "f"+ u"é"+ "rence: %s " %invoice_number]], [10*cm], 1*[0.5*cm], hAlign='LEFT')
    #elements.append( _infos_iban )
    #elements.append(_pouracquit_signature)
    _file_name = '-'.join([a.invoice_number for a in queryset.order_by("invoice_number")])
    _payment_ref = _file_name.replace(" ", "")[:10]
    elements.extend(_build_recap(_recap_date, _payment_ref, recapitulatif_data))
    return {"elements" : elements
            , "invoice_number" : invoice_number
            , "patient_name" : patientName + " " + patientFirstName
            , "invoice_amount" : newData[23][5]}

pdf_private_invoice_with_recap.short_description = "Participation P. avec recapitulatif"

def _compute_sum(data, position):
    sum = 0
    for x in data:
        if x[position] != "" :
            sum += decimal.Decimal(x[position])
    return sum

def _build_recap(_recap_date, _recap_ref, recaps):
    """
    """
    elements = []

    _intro = Table([["Veuillez trouver ci-joint le r"+ u"é"+ "capitulatif des factures ainsi que le montant total " + u"à" +" payer"]], [10*cm, 5*cm], 1*[0.5*cm], hAlign='LEFT')
    elements.append(_intro)
    elements.append(Spacer(1, 18))

    data = []
    i = 0
    data.append(("N d'ordre", u"Note no°", u"Nom et prénom", "Montant" ))
    total = 0.0
    _invoice_nrs = "";
    for recap in recaps:
        i+=1
        data.append((i, recap[0], recap[1], recap[2]))
        total = decimal.Decimal(total) + decimal.Decimal(recap[2])
        _invoice_nrs += "-" + recap[0]
    data.append(("", "", u"à reporter", round(total, 2), ""))

    table = Table(data, [2*cm, 3*cm , 7*cm, 3*cm], (i+2)*[0.75*cm] )
    table.setStyle(TableStyle([('ALIGN',(1,1),(-2,-2),'LEFT'),
                       ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                       ('FONTSIZE', (0,0), (-1,-1), 9),
                       ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                       ]))
    elements.append(table)



    elements.append(Spacer(1, 18))

    elements.append(Spacer(1, 18))
    _infos_iban = Table([["Lors du virement, veuillez indiquer la r" + u"é" + "f" + u"é" + "rence: %s " % _recap_ref]], [10 * cm], 1 * [0.5 * cm], hAlign='LEFT')
    _date_infos = Table([["Date facture : %s " % _recap_date]], [10 * cm], 1 * [0.5 * cm], hAlign='LEFT')

    elements.append(_date_infos)
    elements.append(Spacer(1, 18))
    elements.append(_infos_iban)
    elements.append(Spacer(1, 18))
    _total_a_payer = Table([["Total "+ u"à"+ " payer:",  "%10.2f Euros" % total]], [10*cm, 5*cm], 1*[0.5*cm], hAlign='LEFT')
    elements.append(_total_a_payer)
    elements.append(Spacer(1, 18))

    _infos_iban = Table([["Num"  + u"é" + "ro IBAN: LU55 0019 4555 2516 1000 BCEELULL"]], [10*cm], 1*[0.5*cm], hAlign='LEFT')
    elements.append( _infos_iban )

    return elements

    
    
