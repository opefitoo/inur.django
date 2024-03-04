# -*- coding: utf-8 -*-
import csv
import datetime
import io
import os

from django.http import HttpResponse, FileResponse
from django.utils.translation import gettext_lazy as _
from pypdf import PdfMerger
from reportlab.lib.units import cm
from reportlab.platypus.doctemplate import SimpleDocTemplate

from invoices.invoiceitem_pdf import get_doc_elements
from invoices.models import InvoiceItemPrescriptionsList


def export_to_pdf(modeladmin, request, queryset):
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    # Append invoice number and invoice date
    if len(queryset) != 1:
        _file_name = '-'.join([a.invoice_number for a in queryset.order_by("invoice_number")])
        response['Content-Disposition'] = 'attachment; filename="invoice%s.pdf"' % (_file_name.replace(" ", "")[:150])
    else:
        response['Content-Disposition'] = 'attachment; filename="invoice-%s-%s-%s.pdf"' % (queryset[0].patient.name,
                                                                                           queryset[0].invoice_number,
                                                                                           queryset[
                                                                                               0].invoice_date.strftime(
                                                                                               '%d-%m-%Y'))

    doc = SimpleDocTemplate(response, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
    elements, files = get_doc_elements(queryset, False)
    doc.build(elements)

    return response


export_to_pdf.short_description = _("CNS Invoice")


def link_invoice_to_invoice_batch(modeladmin, request, queryset):
    if not request.user.is_superuser:
        return
    # first create a new invoice batch
    from invoices.models import InvoiceItemBatch
    first_invoice_date = queryset.order_by("invoice_date").first().invoice_date
    last_invoice_date = queryset.order_by("invoice_date").last().invoice_date
    new_invoice_batch = InvoiceItemBatch.objects.create(start_date=first_invoice_date, end_date=last_invoice_date,
                                                        batch_description="Batch created by {0}".format(request.user))
    # now link all invoices that are not already linked another batch to this batch
    queryset.filter(batch__isnull=True).update(batch=new_invoice_batch)
    # now update the batch
    new_invoice_batch.save()
    modeladmin.message_user(request, "Batch {0} created and linked to {1} invoices".format(new_invoice_batch,
                                                                                           queryset.filter(
                                                                                               batch__isnull=True).count()))

def generate_forfaits_infirmiers_mars_avril_mai(modeladmin, request, queryset):
    if not request.user.is_superuser:
        return
    # first create a new invoice batch
    from invoices.models import InvoiceItemBatch
    from invoices.models import InvoiceItem
    first_invoice_date = queryset.order_by("invoice_date").first().invoice_date
    last_invoice_date = queryset.order_by("invoice_date").last().invoice_date
    new_invoice_batch = InvoiceItemBatch.objects.create(start_date=first_invoice_date, end_date=last_invoice_date,
                                                        batch_description="Batch created by {0}".format(request.user))
    # now link all invoices that are not already linked another batch to this batch
    invoices = InvoiceItem.objects.filter(invoice_date__gte=datetime.date(2020, 3, 1), invoice_date__lte=datetime.date(2020, 6, 30),
                               created_by='script_assurance_dependance').update(batch=new_invoice_batch)
    # add the invoice items to the batch
    new_invoice_batch.invoice_items.add(*invoices)
    # now update the batch
    new_invoice_batch.save()
    modeladmin.message_user(request, "Batch {0} created and linked to {1} invoices".format(new_invoice_batch,
                                                                                           queryset.filter(
                                                                                               batch__isnull=True).count()))


def find_all_invoice_items_with_broken_file(modeladmin, request, queryset):
    broken_items = []
    for invoice in queryset:
        if InvoiceItemPrescriptionsList.objects.filter(invoice_item=invoice).exists():
            all_prescriptions = InvoiceItemPrescriptionsList.objects.filter(invoice_item=invoice).all()
            for prescription in all_prescriptions:
                try:
                    print(prescription.medical_prescription.file_upload.file.name)
                except FileNotFoundError as e:
                    print(e)
                    broken_items.append(prescription)
    if len(broken_items) > 0:
        # export broken items to csv
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="broken_items.csv"'
        writer = csv.writer(response)
        writer.writerow(['Invoice', 'Patient', 'Prescription', 'url'])
        for item in broken_items:
            url = "https://surlu2023.herokuapp.com/admin/invoices/medicalprescription/%s/change/" % item.medical_prescription.id
            writer.writerow(
                [item.invoice_item.invoice_number, item.invoice_item.patient.name, item.medical_prescription, url])
        return response
    else:
        modeladmin.message_user(request, _("No broken file found"))


def find_all_medical_prescriptions_and_merge_them_in_one_file(modeladmin, request, queryset):
    if not request.user.is_superuser:
        return
    unbroken_items = []
    merger = PdfMerger()
    for invoice in queryset:
        if InvoiceItemPrescriptionsList.objects.filter(invoice_item=invoice).exists():
            all_prescriptions = InvoiceItemPrescriptionsList.objects.filter(invoice_item=invoice).all()
            for prescription in all_prescriptions:
                if prescription.medical_prescription.file_upload is None:
                    continue
                try:
                    print(prescription.medical_prescription.file_upload.file.name)
                    merger.append(prescription.medical_prescription.file_upload.file)
                except FileNotFoundError as e:
                    print(e)
                finally:
                    unbroken_items.append(prescription)
    pdf_buffer = io.BytesIO()
    merger.write(pdf_buffer)

    pdf_buffer.seek(0)
    response = FileResponse(pdf_buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename=merged_files.pdf'
    return response


find_all_medical_prescriptions_and_merge_them_in_one_file.short_description = _(
    "Trouver toutes les ordonnances et les fusionner dans un seul fichier")


def set_invoice_as_paid(modeladmin, request, queryset):
    if request.user.is_superuser:
        queryset.update(invoice_paid=True)
        modeladmin.message_user(request, _("Invoice(s) marked as paid"))
    else:
        modeladmin.message_user(request, _("You are not allowed to do this action"))


set_invoice_as_paid.short_description = _("Mark invoice(s) as paid")


def set_invoice_as_not_sent(modeladmin, request, queryset):
    if request.user.is_superuser:
        queryset.update(invoice_sent=False)
        modeladmin.message_user(request, _("Invoice(s) marked as not sent"))
    else:
        modeladmin.message_user(request, _("You are not allowed to do this action"))


set_invoice_as_not_sent.short_description = _("Mark invoice(s) as not sent")


def set_invoice_as_sent(modeladmin, request, queryset):
    if request.user.is_superuser:
        queryset.update(invoice_sent=True)
        modeladmin.message_user(request, _("Invoice(s) marked as sent"))
    else:
        modeladmin.message_user(request, _("You are not allowed to do this action"))


set_invoice_as_sent.short_description = _("Mark invoice(s) as sent")


def set_invoice_as_not_paid(modeladmin, request, queryset):
    if request.user.is_superuser:
        queryset.update(invoice_paid=False)
        modeladmin.message_user(request, _("Invoice(s) marked as not paid"))
    else:
        modeladmin.message_user(request, _("You are not allowed to do this action"))


set_invoice_as_not_paid.short_description = _("Mark invoice(s) as not paid")


def export_to_pdf_with_medical_prescription_files(modeladmin, request, queryset):
    # Create the HttpResponse object with the appropriate PDF headers.
    response = HttpResponse(content_type='application/pdf')
    # Append invoice number and invoice date
    if len(queryset) != 1:
        _file_name = '-'.join([a.invoice_number for a in queryset.order_by("invoice_number")])
        response['Content-Disposition'] = 'attachment; filename="invoice%s.pdf"' % (_file_name.replace(" ", "")[:150])
    else:
        response['Content-Disposition'] = 'attachment; filename="invoice-%s-%s-%s.pdf"' % (queryset[0].patient.name,
                                                                                           queryset[0].invoice_number,
                                                                                           queryset[
                                                                                               0].invoice_date.strftime(
                                                                                               '%d-%m-%Y'))

    doc = SimpleDocTemplate(response, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm, bottomMargin=1 * cm)
    elements, files = get_doc_elements(queryset, True)
    doc.build(elements)

    return response


export_to_pdf_with_medical_prescription_files.short_description = "Facture CNS (avec Prescriptions inclues)"


def create_google_contact(modeladmin, request, queryset):
    if not request.user.is_superuser:
        modeladmin.message_user(request, _("You are not allowed to do this action"))
        return
    from invoices.processors.tasks import sync_google_contacts
    if os.environ.get('LOCAL_ENV', None):
        sync_google_contacts(queryset)
    else:
        sync_google_contacts.delay(queryset)

def cleanup_contacts(modeladmin, request, queryset):
    from invoices.processors.tasks import delete_all_contacts
    if os.environ.get('LOCAL_ENV', None):
        delete_all_contacts(queryset)
    else:
        delete_all_contacts.delay(queryset)

def cleanup_some_contacts(modeladmin, request, queryset):
    if not request.user.is_superuser:
        modeladmin.message_user(request, _("You are not allowed to do this action"))
        return
    from invoices.processors.tasks import delete_some_contacts
    if os.environ.get('LOCAL_ENV', None):
        delete_some_contacts(queryset)
    else:
        delete_some_contacts.delay(queryset)
