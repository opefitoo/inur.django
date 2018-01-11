# -*- coding: utf-8 -*-
from __future__ import print_function
import sys
import requests
from django.http import HttpResponse
from django.utils import timezone
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
    #response = HttpResponse(content_type='application/pdf')
    now = timezone.now()
    #response['Content-Disposition'] = 'attachment; filename="road-book-2016-%s.pdf"' % now.strftime('%d-%m-%Y')
    #name_map = {'zipcode': 'zipcode', 'address': 'address', 'pk': 'id'}


    #allyear_patients = Patient.objects.raw("select prst.date,p.* from invoices_invoiceitem pr, invoices_patient p, invoices_carecode cc, invoices_prestation prst where cc.id = prst.carecode_id and cc.code like '%NF%' and pr.patient_id = p.id and prst.date >= '2016-01-01' and prst.date <= '2016-12-31' and prst.invoice_item_id = pr.id group by prst.date,p.id order by prst.date asc")

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
    for p in row:
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

        writer.writerow([p[4].encode('utf-8').strip() + ' ' + p[3].encode('utf-8').strip(),
                     _patient_address.encode('utf-8').strip(),
                     (p[0]).strftime('%d/%m/%Y %H:%M'),
                     pdistance])

        _point_start = _point_end



    #doc.build(elements)

    return response
