# -*- coding: utf-8 -*-

import datetime


from invoices.models import Patient, InvoiceItem, CareCode, ValidityDate  # , PrivateInvoiceItem
from django.http import HttpResponseRedirect, HttpResponse


def previous_months_invoices_jan(modeladmin, request, queryset):
    # response = HttpResponse(content_type='text')
    previous_month_patients = Patient.objects.raw ("SELECT "
                                                    + "    pat.id, "
                                                    + "    pat.name, "
                                                    + "    pat.first_name,"
                                                    + "    pat.code_sn "
                                                    + "FROM "
                                                    + "    invoices_prestation out, "
                                                    + "    invoices_patient pat, "
                                                    + "    invoices_carecode cod "
                                                    + "WHERE "
                                                    + "    out.date > '2016-12-31' "
                                                    + "    AND out.date < '2017-02-01' "
                                                    + "    AND pat.id = out.patient_id "
                                                    + "    AND pat.is_private = 'f' "
                                                    + "    AND cod.id = out.carecode_id "
                                                    + "    AND cod.reimbursed = TRUE "
                                                    + "    AND out.id NOT IN( "
                                                    + "        SELECT "
                                                    + "            prest.id "
                                                    + "        FROM "
                                                    + "            public.invoices_invoiceitem_prestations rel, "
                                                    + "            invoices_prestation prest "
                                                    + "        WHERE "
                                                    + "            prest.date > '2016-12-31' "
                                                    + "            AND prest.date < '2017-02-01' "
                                                    + "            AND rel.prestation_id = prest.id "
                                                    + "    ) GROUP BY pat.id")

    invoice_counters = 0
    for p in previous_month_patients:
        currInvoices = InvoiceItem.objects.filter(patient__code_sn=p.code_sn).filter(invoice_date__range=["2017-01-01", "2017-01-31"])
        if currInvoices.exists():
            currInvoices[0].clean()
            currInvoices[0].save()
        else:
            invoiceitem = InvoiceItem (patient=p,
                                   invoice_date=datetime.datetime (2017, 1, 31),
                                   invoice_sent=False,
                                   invoice_paid=False)

            invoiceitem.clean ()
            invoiceitem.save ()
            invoice_counters += 1


def previous_months_invoices_feb(modeladmin, request, queryset):
    # response = HttpResponse(content_type='text')

        # response = HttpResponse(content_type='text')
    previous_month_patients = Patient.objects.raw ("SELECT "
                                                       + "    pat.id, "
                                                       + "    pat.name, "
                                                       + "    pat.first_name,"
                                                       + "    pat.code_sn "
                                                       + "FROM "
                                                       + "    invoices_prestation out, "
                                                       + "    invoices_patient pat, "
                                                       + "    invoices_carecode cod "
                                                       + "WHERE "
                                                       + "    out.date > '2017-01-31' "
                                                       + "    AND out.date < '2017-03-01' "
                                                       + "    AND pat.id = out.patient_id "
                                                       + "    AND pat.is_private = 'f' "
                                                       + "    AND cod.id = out.carecode_id "
                                                       + "    AND cod.reimbursed = TRUE "
                                                       + "    AND out.id NOT IN( "
                                                       + "        SELECT "
                                                       + "            prest.id "
                                                       + "        FROM "
                                                       + "            public.invoices_invoiceitem_prestations rel, "
                                                       + "            invoices_prestation prest "
                                                       + "        WHERE "
                                                       + "            prest.date > '2017-01-31' "
                                                       + "            AND prest.date < '2017-03-01' "
                                                       + "            AND rel.prestation_id = prest.id "
                                                       + "    ) GROUP BY pat.id")

    invoice_counters = 0
    for p in previous_month_patients:
        currInvoices = InvoiceItem.objects.filter (patient__code_sn=p.code_sn).filter (invoice_date__range=["2017-02-01", "2017-02-28"])
        if currInvoices.exists ():
            currInvoices[0].clean ()
            currInvoices[0].save ()
        else:
             invoiceitem = InvoiceItem (patient=p,
                                        invoice_date=datetime.datetime (2017, 2, 28),
                                        invoice_sent=False,
                                        invoice_paid=False)
             invoiceitem.clean ()
             invoiceitem.save ()
             invoice_counters += 1


def previous_months_invoices_april(modeladmin, request, queryset):
    # response = HttpResponse(content_type='text')

        # response = HttpResponse(content_type='text')
    previous_month_patients = Patient.objects.raw ("SELECT "
                                                       + "    pat.id, "
                                                       + "    pat.name, "
                                                       + "    pat.first_name,"
                                                       + "    pat.code_sn "
                                                       + "FROM "
                                                       + "    invoices_prestation out, "
                                                       + "    invoices_patient pat, "
                                                       + "    invoices_carecode cod "
                                                       + "WHERE "
                                                       + "    out.date >= '2017-04-01' "
                                                       + "    AND out.date <= '2017-04-30' "
                                                       + "    AND pat.id = out.patient_id "
                                                       + "    AND pat.is_private = 'f' "
                                                       + "    AND cod.id = out.carecode_id "
                                                       + "    AND cod.reimbursed = TRUE "
                                                       + "    AND out.id NOT IN( "
                                                       + "        SELECT "
                                                       + "            prest.id "
                                                       + "        FROM "
                                                       + "            public.invoices_invoiceitem_prestations rel, "
                                                       + "            invoices_prestation prest "
                                                       + "        WHERE "
                                                       + "            prest.date >= '2017-04-01' "
                                                       + "            AND prest.date <= '2017-04-30' "
                                                       + "            AND rel.prestation_id = prest.id "
                                                       + "    ) GROUP BY pat.id")

    invoice_counters = 0
    for p in previous_month_patients:
        currInvoices = InvoiceItem.objects.filter (patient__code_sn=p.code_sn).filter (invoice_date__range=["2017-04-01", "2017-04-30"])
        if currInvoices.exists ():
            currInvoices[0].clean ()
            currInvoices[0].save ()
        else:
             invoiceitem = InvoiceItem (patient=p,
                                        invoice_date=datetime.datetime (2017, 4, 30),
                                        invoice_sent=False,
                                        invoice_paid=False)
             invoiceitem.clean ()
             invoiceitem.save ()
             invoice_counters += 1


def previous_months_invoices_july_2017(modeladmin, request, queryset):
    # response = HttpResponse(content_type='text')

        # response = HttpResponse(content_type='text')
    previous_month_patients = Patient.objects.raw ("SELECT "
                                                       + "    pat.id, "
                                                       + "    pat.name, "
                                                       + "    pat.first_name,"
                                                       + "    pat.code_sn "
                                                       + "FROM "
                                                       + "    invoices_prestation out, "
                                                       + "    invoices_patient pat, "
                                                       + "    invoices_carecode cod "
                                                       + "WHERE "
                                                       + "    out.date >= '2017-07-01' "
                                                       + "    AND out.date <= '2017-07-31' "
                                                       + "    AND pat.id = out.patient_id "
                                                       + "    AND pat.is_private = 'f' "
                                                       + "    AND cod.id = out.carecode_id "
                                                       + "    AND cod.reimbursed = TRUE "
                                                       + "    AND out.id NOT IN( "
                                                       + "        SELECT "
                                                       + "            prest.id "
                                                       + "        FROM "
                                                       + "            public.invoices_invoiceitem_prestations rel, "
                                                       + "            invoices_prestation prest "
                                                       + "        WHERE "
                                                       + "            prest.date >= '2017-07-01' "
                                                       + "            AND prest.date <= '2017-07-31' "
                                                       + "            AND rel.prestation_id = prest.id "
                                                       + "    ) GROUP BY pat.id")

    invoice_counters = 0
    for p in previous_month_patients:
        currInvoices = InvoiceItem.objects.filter (patient__code_sn=p.code_sn).filter (invoice_date__range=["2017-07-01", "2017-07-31"])
        if currInvoices.exists ():
            currInvoices[0].clean ()
            currInvoices[0].save ()
        else:
             invoiceitem = InvoiceItem (patient=p,
                                        invoice_date=datetime.datetime (2017, 7, 31),
                                        invoice_sent=False,
                                        invoice_paid=False)
             invoiceitem.clean ()
             invoiceitem.save ()
             invoice_counters += 1








def create_invoice_for_health_insurance(modeladmin, request, queryset):
    # response = HttpResponse(content_type='text')

    from collections import defaultdict

    prestations_to_invoice = defaultdict (list)
    invoices_created = []
    invpks = []
    # for p in queryset:
    #     if PrivateInvoiceItem.objects.filter (prestations__id=p.pk).count () == 0 and InvoiceItem.objects.filter (
    #             prestations__id=p.pk).count () == 0:
    #         prestations_to_invoice[p.patient].append (p)

    _private_patient_flag = False
    for k, v in prestations_to_invoice.iteritems ():
        if (k.private_patient):
            # invoiceitem = PrivateInvoiceItem (private_patient=k,
            #                                   invoice_date=datetime.datetime.now (),
            #                                   invoice_sent=False,
            #                                   invoice_paid=False)
            _private_patient_flag = True
        else:
            invoiceitem = InvoiceItem (patient=k,
                                       invoice_date=datetime.datetime.now (),
                                       invoice_sent=False,
                                       invoice_paid=False)
            _private_patient_flag = False
            invoices_created.append (invoiceitem)
            invpks.append(invoiceitem.pk)
        invoiceitem.save()
        for prestav in v:
            invoiceitem.prestations.add (prestav)

    # return HttpResponseRedirect("/admin/invoices/invoiceitem/?ct=%s&ids=%s" % (invoiceitem.pk, ",".join(invpks)))
    if not _private_patient_flag:
        return HttpResponseRedirect ("/admin/invoices/invoiceitem/")
    # else:
    #     return HttpResponseRedirect ("/admin/invoices/privateinvoiceitem/")


create_invoice_for_health_insurance.short_description = u"Créer une facture pour CNS"

