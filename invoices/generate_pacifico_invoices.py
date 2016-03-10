# -*- coding: utf-8 -*-
import calendar
from datetime import date,timedelta

from invoices.models import Patient, Prestation, CareCode, PrivateInvoiceItem


def generate_pacifico(modeladmin, request, queryset):
    # response = HttpResponse(content_type='text')

    paolaPacifico = Patient.objects.get(name="PACIFICO")

    distrib_medocs_ant1 = CareCode.objects.get(code="ANT1")
    prepa_medocs_hebdo_ant3 = CareCode.objects.get(code="ANT3")

    d1 = date(2015,6,30)
    d2 = date(2015,12,31)

    dd = [d1 + timedelta(days=x) for x in range((d2-d1).days + 1)]
    import datetime
    for d in dd:
        if(d.weekday() == 0):
            try:
                p1 = Prestation(patient=paolaPacifico, carecode=prepa_medocs_hebdo_ant3, date= datetime.datetime.combine(d, datetime.time(8, 0)))
                p1.clean()
                p1.save()
            except Exception as e:
                print e

            try:
                p2 = Prestation(patient=paolaPacifico, carecode=distrib_medocs_ant1, date= datetime.datetime.combine(d, datetime.time(20, 0)))
                p2.clean()
                p2.save()
            except Exception as e:
                print e
        if(d.weekday() == 2):
            try:
                p1 = Prestation(patient=paolaPacifico, carecode=distrib_medocs_ant1, date= datetime.datetime.combine(d, datetime.time(8, 0)))
                p1.clean()
                p1.save()
            except Exception as e:
                print e
            try:
                p2 = Prestation(patient=paolaPacifico, carecode=distrib_medocs_ant1, date= datetime.datetime.combine(d, datetime.time(20, 0)))
                p2.clean()
                p2.save()
            except Exception as e:
                print e

        if(d.weekday() == 4):
            try:
                p1 = Prestation(patient=paolaPacifico, carecode=distrib_medocs_ant1, date= datetime.datetime.combine(d, datetime.time(8, 0)))
                p1.clean()
                p1.save()
            except Exception as e:
                print e
            try:
                p2 = Prestation(patient=paolaPacifico, carecode=distrib_medocs_ant1, date= datetime.datetime.combine(d, datetime.time(20, 0)))
                p2.clean()
                p2.save()
            except Exception as e:
                print e


    invoiceitem= PrivateInvoiceItem(private_patient=paolaPacifico,
                                  invoice_date=datetime.datetime(2016, 03, 14),
                                  invoice_sent=False,
                                  invoice_paid=False,
                                  medical_prescription_date = datetime.datetime(2014, 10, 14))
    invoiceitem.clean()
    invoiceitem.save()