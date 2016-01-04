# -*- coding: utf-8 -*-
from django.http import HttpResponse
from invoices.models import Patient
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

def generate(modeladmin, request, queryset):
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    # Append invoice number and invoice date
    if len(queryset) != 1:
        _file_name = '-'.join([a.invoice_number for a in queryset.order_by("invoice_number")])
        response['Content-Disposition'] = 'attachment; filename="invoice%s.pdf"' %(_file_name.replace(" ", "")[:150])
    else:
        response['Content-Disposition'] = 'attachment; filename="invoice-%s-%s-%s-part-personnelle.pdf"' %(queryset[0].patient.name,
                                                                                          queryset[0].invoice_number,
                                                                                          queryset[0].invoice_date.strftime('%d-%m-%Y'))

    allyear_patients = Patient.objects.raw("select pr.date,p.* from invoices_prestation pr, invoices_patient p, invoices_carecode cc  where cc.id = pr.carecode_id and cc.code = 'NF1' and pr.patient_id = p.id  and pr.date >= '2014-01-01' and pr.date <= '2014-12-31'  group by pr.date,p.id order by pr.date asc")
    allyear_patients.db
    import requests
    r = requests.get('http://maps.googleapis.com/maps/api/distancematrix/json?origins=fort%20wallis,luxembourg&destinations=metz&mode=car&language=en-EN&sensor=false')
    #r = requests.get('http://yahoo.fr')
    r.status_code
    json_result = r.json()

    elements = []
    data = []
    data.append(('Nom Patient', 'Adresse', 'Date' ,'Distance parcourue'))
    from django.utils import timezone
    now = timezone.now()
    for p in allyear_patients:
        _patient_address = u"%s %s, %s"%(p.address, p.zipcode, p.city)
        if now != p.date:
            _point_start = "1A rue fort wallis,Luxembourg"
        else:
            _point_start = _point_start
        now = p.date
        _point_end = _patient_address
        r = requests.get('http://maps.googleapis.com/maps/api/distancematrix/json?origins=fort%s&destinations=%s&mode=car&language=en-EN&sensor=false'%(_point_start, _point_end))
        if r.status_code == 200 and 'OK' == r.json()['status'] and r.json()['rows'][0]['elements'][0]['status'] != u'NOT_FOUND':
            pdistance = r.json()['rows'][0]['elements'][0]['distance']['text']
        else:
            pdistance = 0
        data.append(( p.name + ' ' + p.first_name,
                      _patient_address ,
                     (p.date).strftime('%d/%m/%Y %H:%M'),
                     pdistance))
        _point_start = _point_end

    table = Table(data, [7*cm, 9*cm, 2.5*cm, 2*cm], len(data)*[1*cm] )
    table.setStyle(TableStyle([('ALIGN',(1,1),(-2,-2),'LEFT'),
                       ('INNERGRID', (0,0), (-1,-1), 0.25, colors.black),
                       ('ALIGN',(0,-1), (-6,-1),'RIGHT'),
                       ('INNERGRID', (0,-1), (-6,-1), 0, colors.white),
                       ('ALIGN',(0,-2), (-6,-2),'RIGHT'),
                       ('INNERGRID', (0,-2), (-6,-2), 0, colors.white),
                       ('FONTSIZE', (0,0), (-1,-1), 8),
                       ('BOX', (0,0), (-1,-1), 0.25, colors.black),
                       ]))

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    elements.append(table)
    doc = SimpleDocTemplate(response, rightMargin=2*cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1*cm)


    doc.build(elements)
    return response

