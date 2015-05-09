# -*- coding: utf-8 -*-

import datetime

from models import Patient, InvoiceItem


def previous_months_invoices_october(modeladmin, request, queryset):
    
    #response = HttpResponse(content_type='text')
    
    previous_month_patients = Patient.objects.raw("select p.id, p.name, p.first_name "+  
        "from public.invoices_patient p, public.invoices_prestation prest "+
        "where p.id = prest.patient_id "+
        "and prest.date between '2014-10-01'::DATE and '2014-11-01'::DATE "+ 
        "and p.private_patient = 'f' "+
        "and (select count(inv.id) from public.invoices_invoiceitem inv "+
        "where inv.invoice_date between '2014-10-01'::DATE and '2014-11-01'::DATE "+ 
        "and inv.patient_id = p.id) = 0" + 
        "group by p.id "+
        "order by p.name")
    invoice_counters = 0
    for p in previous_month_patients:
        invoiceitem = InvoiceItem(patient=p,
                                  invoice_date=datetime.datetime(2014, 10, 31),
                                  invoice_sent=False,
                                  invoice_paid=False)
        invoiceitem.clean()
        invoiceitem.save()
        invoice_counters  = invoice_counters + 1 
    
