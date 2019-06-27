# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
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
# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def generate_road_book_2016(modeladmin, request, queryset):
    import  datetime
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    now = timezone.now()
    response['Content-Disposition'] = 'attachment; filename="road-book-2016-%s.pdf"' % now.strftime('%d-%m-%Y')
    name_map = {'zipcode': 'zipcode', 'address': 'address', 'pk': 'id'}


    allyear_patients = Patient.objects.raw("select prst.date,p.* from invoices_invoiceitem pr, invoices_patient p, invoices_carecode cc, invoices_prestation prst where cc.id = prst.carecode_id and cc.code like '%NF%' and pr.patient_id = p.id and prst.date >= '2016-01-01' and prst.date <= '2016-12-31' and prst.invoice_item_id = pr.id group by prst.date,p.id order by prst.date asc")

    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("select prst.date,p.* from invoices_invoiceitem pr, invoices_patient p, invoices_carecode cc, invoices_prestation prst where cc.id = prst.carecode_id and cc.code like '%NF%' and pr.patient_id = p.id and prst.date >= '2016-01-01' and prst.date <= '2016-12-31' and prst.invoice_item_id = pr.id group by prst.date,p.id order by prst.date asc")
        row = cursor.fetchall()

    elements = []
    data = []
    #data.append(('Nom Patient', 'Adresse', 'Date', 'Distance'))

    import csv
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="roadbook2016.csv"'

    writer = csv.writer(response)
    writer.writerow(['Nom Patient', 'Adresse', 'Date', 'Distance'])


    sumdistance = 0
    counter = 1
    for p in row:
        counter = counter + 1
        if counter == 5:
            break
        _patient_address = u"%s %s, %s" % (p[5], p[6], p[7])
        if now != p[0]:
            _point_start = "1A rue fort wallis,Luxembourg"
        else:
            _point_start = _point_start
        now = p[0]
        _point_end = _patient_address
        r = requests.get(
            'https://maps.googleapis.com/maps/api/distancematrix/json?origins=fort%s&destinations=%s&mode=car&language=en-EN&sensor=false' % (
                _point_start, _point_end))
        if r.status_code == 200 and 'OK' == r.json()['status'] and r.json()['rows'][0]['elements'][0][
            'status'] != u'NOT_FOUND':
            pdistance = r.json()['rows'][0]['elements'][0]['distance']['text']
            sumdistance += r.json()['rows'][0]['elements'][0]['distance']['value']
        elif r.status_code == 200 and 'OK' == r.json()['status'] and r.json()['rows'][0]['elements'][0][
            'status'] == u'NOT_FOUND':
            _point_start = p[7]
            r = requests.get(
                'https://maps.googleapis.com/maps/api/distancematrix/json?origins=fort%s&destinations=%s&mode=car&language=en-EN&sensor=false' % (
                    _point_start, _point_end))

            # should be 'https://maps.googleapis.com/maps/api/distancematrix/json?origins=fort%s&destinations=%s&mode=car&language=en-EN&sensor=false&key=XXXX' % (_point_start, _point_end))


            if r.status_code == 200 and 'OK' == r.json()['status'] and r.json()['rows'][0]['elements'][0][
                'status'] != u'NOT_FOUND':
                pdistance = r.json()['rows'][0]['elements'][0]['distance']['text']
                sumdistance += r.json()['rows'][0]['elements'][0]['distance']['value']
            else:
                pdistance = 0
                _point_end = _point_start
                # Log an error message
                eprint('Something went wrong!', r.json()['status'],
                       r.json()['status'] and r.json()['rows'][0]['elements'][0][
                           'status'], "p.end:" + _point_end, "p.start:" + _point_start,
                       r.json()['rows'][0]['elements'][0], sep='--')

        else:
            pdistance = 0
            _point_end = _point_start
            # Log an error message
            eprint('Something went wrong!', r.json()['status'],
                   r.json()['status'] and r.json()['rows'][0]['elements'][0][
                       'status'], "p.end:" + _point_end, "p.start:" + _point_start, r.json()['rows'][0]['elements'][0],
                   sep='--')

            writer.writerow([p[4] + ' ' + p[3],
                     _patient_address,
                     (p[0]).strftime('%d/%m/%Y %H:%M'),
                     pdistance])

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
    elements.append(Paragraph(u"Livre de bord pour l'année 2016 (génération automatique)", styles['Center']))
    elements.append(table)
    elements.append(Spacer(1, 18))
    elements.append(
        Paragraph("La distance totale parcourue en 2016 est de %s KM" % (sumdistance / 1000), styles['Center']))
    doc = SimpleDocTemplate(response, pagesize=letter, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm,
                            bottomMargin=1 * cm)

    #doc.build(elements)

    return response
