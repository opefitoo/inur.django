# -*- coding: utf-8 -*-
import requests
from django.http import HttpResponse
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus.doctemplate import SimpleDocTemplate
from reportlab.platypus.flowables import Spacer
from reportlab.platypus.para import Paragraph
from reportlab.platypus.tables import Table, TableStyle
from invoices.models import Patient

def generate_road_book_2014(modeladmin, request, queryset):
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    now = timezone.now()
    response['Content-Disposition'] = 'attachment; filename="road-book-2014-%s.pdf"' % now.strftime('%d-%m-%Y')

    allyear_patients = Patient.objects.raw(
        "select pr.date,p.* from invoices_prestation pr, invoices_patient p, invoices_carecode cc  where cc.id = pr.carecode_id and cc.code = 'NF1' and pr.patient_id = p.id  and pr.date >= '2014-01-01' and pr.date <= '2014-12-31' group by pr.date,p.id order by pr.date asc")
    allyear_patients.db

    elements = []
    data = []
    data.append(('Nom Patient', 'Adresse', 'Date', 'Distance'))

    sumdistance = 0
    for p in allyear_patients:
        _patient_address = u"%s %s, %s" % (p.address, p.zipcode, p.city)
        if now != p.date:
            _point_start = "1A rue fort wallis,Luxembourg"
        else:
            _point_start = _point_start
        now = p.date
        _point_end = _patient_address
        r = requests.get(
            'http://maps.googleapis.com/maps/api/distancematrix/json?origins=fort%s&destinations=%s&mode=car&language=en-EN&sensor=false' % (
            _point_start, _point_end))
        if r.status_code == 200 and 'OK' == r.json()['status'] and r.json()['rows'][0]['elements'][0][
            'status'] != u'NOT_FOUND':
            pdistance = r.json()['rows'][0]['elements'][0]['distance']['text']
            sumdistance += r.json()['rows'][0]['elements'][0]['distance']['value']
        else:
            pdistance = 0
            _point_end = _point_start

        data.append((p.name + ' ' + p.first_name,
                     _patient_address,
                     (p.date).strftime('%d/%m/%Y %H:%M'),
                     pdistance))
        _point_start = _point_end

    table = Table(data, [7 * cm, 9 * cm, 2.5 * cm, 2 * cm], len(data) * [0.8 * cm])

    table.setStyle(TableStyle([('ALIGN', (1, 1), (-2, -2), 'LEFT'),
                               ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black),
                               ('ALIGN', (0, -1), (-6, -1), 'RIGHT'),
                               ('ALIGN', (0, -2), (-6, -2), 'RIGHT'),
                               ('FONTSIZE', (0, 0), (-1, -1), 7),
                               ('BOX', (0, 0), (-1, -1), 0.25, colors.black),
                               ]))

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='Center', alignment=TA_CENTER))
    elements.append(Paragraph(u"Livre de bord pour l'année 2014 (génération automatique)", styles['Center']))
    elements.append(table)
    elements.append(Spacer(1, 18))
    elements.append(
        Paragraph("La distance totale parcourue en 2014 est de %s KM" % (sumdistance / 1000), styles['Center']))
    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm,
                            bottomMargin=1 * cm)

    doc.build(elements)
    return response
