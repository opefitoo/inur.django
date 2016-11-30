# -*- coding: utf-8 -*-

import datetime

from models import Patient, InvoiceItem, Prestation, PrivateInvoiceItem
from django.http import HttpResponseRedirect

def previous_months_invoices_july(modeladmin, request, queryset):
    # response = HttpResponse(content_type='text')

    previous_month_patients = Patient.objects.raw("select p.id, p.name, p.first_name " +
                                                  "from public.invoices_patient p, public.invoices_prestation prest " +
                                                  "where p.id = prest.patient_id " +
                                                  "and prest.date >= '2016-07-01'and prest.date <= '2016-07-31' " +
                                                  "and p.private_patient = 'f' " +
                                                  "and (select count(inv.id) from public.invoices_invoiceitem inv " +
                                                  "where inv.invoice_date between '2016-07-01'::DATE and '2016-07-31'::DATE " +
                                                  "and inv.patient_id = p.id) = 0" +
                                                  "group by p.id " +
                                                  "order by p.name")
    invoice_counters = 0
    for p in previous_month_patients:
        invoiceitem = InvoiceItem(patient=p,
                                  invoice_date=datetime.datetime(2016, 7, 31),
                                  invoice_sent=False,
                                  invoice_paid=False)
        invoiceitem.clean()
        invoiceitem.save()
        invoice_counters = invoice_counters + 1


def previous_months_invoices_august(modeladmin, request, queryset):
    # response = HttpResponse(content_type='text')

    previous_month_patients = Patient.objects.raw("select p.id, p.name, p.first_name " +
                                                  "from public.invoices_patient p, public.invoices_prestation prest " +
                                                  "where p.id = prest.patient_id " +
                                                  "and prest.date >= '2016-08-01'and prest.date <= '2016-08-31' " +
                                                  "and p.private_patient = 'f' " +
                                                  "and (select count(inv.id) from public.invoices_invoiceitem inv " +
                                                  "where inv.invoice_date between '2016-08-01'::DATE and '2016-08-31'::DATE " +
                                                  "and inv.patient_id = p.id) = 0" +
                                                  "group by p.id " +
                                                  "order by p.name")
    invoice_counters = 0
    for p in previous_month_patients:
        invoiceitem = InvoiceItem(patient=p,
                                  invoice_date=datetime.datetime(2016, 8, 31),
                                  invoice_sent=False,
                                  invoice_paid=False)
        invoiceitem.clean()
        invoiceitem.save()
        invoice_counters = invoice_counters + 1


def create_invoice_for_health_insurance(modeladmin, request, queryset):
    # response = HttpResponse(content_type='text')

    from collections import defaultdict

    prestations_to_invoice = defaultdict(list)
    invoices_created = []
    invpks = []
    for p in queryset:
        if PrivateInvoiceItem.objects.filter(prestations__id=p.pk).count() == 0 and InvoiceItem.objects.filter(prestations__id=p.pk).count() == 0:
            prestations_to_invoice[p.patient].append(p)

    _private_patient_flag = False
    for k, v in prestations_to_invoice.iteritems():
        if (k.private_patient):
            invoiceitem = PrivateInvoiceItem(private_patient=k,
                                             invoice_date=datetime.datetime.now(),
                                             invoice_sent=False,
                                             invoice_paid=False)
            _private_patient_flag = True
        else:
            invoiceitem = InvoiceItem(patient=k,
                                      invoice_date=datetime.datetime.now(),
                                      invoice_sent=False,
                                      invoice_paid=False)
            _private_patient_flag = False
            invoices_created.append(invoiceitem)
            invpks.append(invoiceitem.pk)
        invoiceitem.save()
        for prestav in v:
            invoiceitem.prestations.add(prestav)

    #return HttpResponseRedirect("/admin/invoices/invoiceitem/?ct=%s&ids=%s" % (invoiceitem.pk, ",".join(invpks)))
    if not _private_patient_flag:
        return HttpResponseRedirect("/admin/invoices/invoiceitem/")
    else:
        return HttpResponseRedirect("/admin/invoices/privateinvoiceitem/")

create_invoice_for_health_insurance.short_description = u"Créer une facture pour CNS"


def create_invoice_for_client_no_irs_reimbursed(modeladmin, request, queryset):
    from collections import defaultdict

    prestations_to_invoice = defaultdict(list)
    invoices_created = []
    invpks = []
    for p in queryset:
        if PrivateInvoiceItem.objects.filter(prestations__id=p.pk).count() == 0 and not p.carecode.reimbursed:
            prestations_to_invoice[p.patient].append(p)

    _private_patient_flag = False
    for k, v in prestations_to_invoice.iteritems():
        if (k.private_patient):
            invoiceitem = PrivateInvoiceItem(private_patient=k,
                                             invoice_date=datetime.datetime.now(),
                                             invoice_sent=False,
                                             invoice_paid=False)
            _private_patient_flag = True
        else:
            invoiceitem = InvoiceItem(patient=k,
                                      invoice_date=datetime.datetime.now(),
                                      invoice_sent=False,
                                      invoice_paid=False)
            invoices_created.append(invoiceitem)
            invpks.append(invoiceitem.pk)
        invoiceitem.save()
        for prestav in v:
            invoiceitem.prestations.add(prestav)


    if not _private_patient_flag:
        return HttpResponseRedirect("/admin/invoices/invoiceitem/")
    else:
        return HttpResponseRedirect("/admin/invoices/privateinvoiceitem/")

create_invoice_for_client_no_irs_reimbursed.short_description = u"Créer une facture pour client avec soins non remboursés"
