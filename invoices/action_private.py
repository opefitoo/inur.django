# -*- coding: utf-8 -*-
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus.doctemplate import SimpleDocTemplate
from reportlab.platypus.flowables import Spacer, PageBreak
from reportlab.platypus.para import Paragraph
from reportlab.platypus.tables import Table, TableStyle
#import pytz
from django.utils.encoding import smart_unicode
import decimal

def pdf_private_invoice(modeladmin, request, queryset):
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    # Append invoice number and invoice date
    if len(queryset) != 1:
        _file_name = '-'.join([a.invoice_number for a in queryset.order_by("invoice_number")])
        response['Content-Disposition'] = 'attachment; filename="invoice%s.pdf"' %(_file_name.replace(" ", "")[:150])
    else:
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
                                      qs.accident_date,
                                      qs.invoice_send_date)
                                      
            elements.extend(_result["elements"])
            recapitulatif_data.append((_result["invoice_number"], _result["patient_name"], _result["invoice_amount"]))
    doc.build(elements)
    return response

def _build_invoices(prestations, invoice_number, invoice_date, prescription_date, accident_id, accident_date, invoice_send_date):
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
        patientFirstName = presta.patient.first_name
        patientAddress = presta.patient.address
        patientZipCode = presta.patient.zipcode
        patientCity = presta.patient.city
        data.append((i, presta.carecode.code, 
                     (presta.date).strftime('%d/%m/%Y'),
                     '1', 
                     presta.carecode.gross_amount, 
                     presta.net_amount, 
                     (presta.date).strftime('%H:%M'),
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
            newData.append(('', '', '', 'Sous-Total', _gross_sum, _net_sum, '', '',''))
    _total_facture = _compute_sum(data[1:], 5)
    newData.append(('', '', '', 'Total', _compute_sum(data[1:], 4), _compute_sum(data[1:], 5), '', '',''))
            
            
    headerData = [['IDENTIFICATION DU FOURNISSEUR DE SOINS DE SANTE\n'
                   + 'Regine SIMBA\n'
                   + '1A, rue fort wallis\n'
                   + 'L-2714 Luxembourg\n'
                   + 'T' + u"é".encode("utf-8") + "l: 691.30.85.84", 
                   'CODE DU FOURNISSEUR DE SOINS DE SANTE\n'
                   + '300744-44'
                   ], 
                  [ u'Matricule patient: %s' % smart_unicode(patientSocNumber.strip()) + "\n" 
                   + u'Nom et Pr'+ smart_unicode("e") + u'nom du patient: %s' % smart_unicode(patientNameAndFirstName) ,
                   u'Nom: %s' % smart_unicode(patientName.strip()) +'\n'
                   + u'Pr' + smart_unicode(u"é") + u'nom: %s' % smart_unicode(patientFirstName.strip()) +'\n'
                   + u'Rue: %s' % patientAddress.strip() + '\n'
                   + u'Code postal: %s' % smart_unicode(patientZipCode.strip()) + '\n'
                   + u'Ville: %s' % smart_unicode(patientCity.strip()) ],
                  [ u'Date accident: %s\n' % (accident_date if accident_date else "")
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
        elements.append(Paragraph("Memoire d'Honoraires Num. %s en date du : %s Ordonnance du %s " %( invoice_number, invoice_date, prescription_date), styles['Heading4']))
    else:
        elements.append(Paragraph("Memoire d'Honoraires Num. %s en date du : %s " %( invoice_number, invoice_date), styles['Heading4']))
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
    _total_a_payer = Table([["Total "+ u"à"+ " payer:",  "%10.2f Euros" % _total_facture ]], [10*cm, 5*cm], 1*[0.5*cm], hAlign='LEFT')
    elements.append(Spacer(1, 18))
    elements.append( _total_a_payer )
    elements.append(Spacer(1, 18))
    
    _pouracquit_signature = Table([["Pour acquit, le:", "Signature et cachet"]], [10*cm, 10*cm], 1*[0.5*cm], hAlign='LEFT')
    
    _infos_iban = Table([[u"À virer sur le compte IBAN: LU55 0019 4555 2516 1000 BCEELULL"]], [10*cm], 1*[0.5*cm], hAlign='LEFT')
    elements.append(Spacer(1, 10))
    elements.append(_infos_iban)
    if prescription_date is not None:
        _infos_iban = Table([["Lors du virement, veuillez indiquer la r"+ u"é" + "f"+ u"é"+ "rence: %s Ordonnance du %s " %(invoice_number,prescription_date)]], [10*cm], 1*[0.5*cm], hAlign='LEFT')
    else:
        _infos_iban = Table([[u"Lors du virement, veuillez indiquer la référence: %s " %invoice_number]], [10*cm], 1*[0.5*cm], hAlign='LEFT')

    if invoice_send_date is not None:
        from utils import setlocale
        with setlocale('fr_FR.utf8'):
            elements.append(Table([["Date envoi de la pr" + u"é" + "sente facture: %s " % invoice_send_date.strftime('%d %B %Y').decode("utf-8")]], [10*cm], 1*[0.5*cm], hAlign='LEFT'))
        elements.append(Spacer(1, 10))

    elements.append( _infos_iban )
    elements.append(_pouracquit_signature)
    return {"elements" : elements
            , "invoice_number" : invoice_number
            , "patient_name" : patientName + " " + patientFirstName
            , "invoice_amount" : newData[23][5]}

pdf_private_invoice.short_description = "Facture PDF"

def _compute_sum(data, position):
    sum = 0
    for x in data:
        if x[position] != "" :
            sum += x[position]
    return sum
