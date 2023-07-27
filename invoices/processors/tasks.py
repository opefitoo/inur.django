import os
import traceback
from datetime import datetime
from datetime import timedelta
from io import BytesIO

from PyPDF2 import PdfMerger
from constance import config
from django.core.files.base import ContentFile
from django_rq import job
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate

from invoices.invoiceitem_pdf import get_doc_elements
from invoices.notifications import notify_system_via_google_webhook
from invoices.prefac import generate_all_invoice_lines


@job
def process_post_save(instance):
    # calculate how much time it takes to process the batch
    start = datetime.now()
    _must_update = False

    if instance.force_update:
        _must_update = True
        instance.version += 1
        instance.force_update = False
    if _must_update:
        from invoices.models import InvoiceItem
        # Now update all InvoiceItems which have an invoice_date within this range
        #if BatchTypeChoices.CNS_INF == instance.batch_type:
            # batch_invoices = InvoiceItem.objects.filter(
            #     Q(invoice_date__gte=instance.start_date) & Q(invoice_date__lte=instance.end_date)).filter(
            #     invoice_sent=False).filter(batch__isnull=True)
            # batch_invoices.update(batch=instance)
        batch_invoices = InvoiceItem.objects.filter(batch=instance)
        file_content = generate_all_invoice_lines(batch_invoices, sending_date=instance.send_date,
                                                  batch_type=instance.batch_type)
        instance.prefac_file = ContentFile(file_content.encode('utf-8'), 'prefac.txt')

        # generate the pdf invoice file
        # Create a BytesIO buffer
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm,
                                bottomMargin=1 * cm)
        elements, copies_of_medical_prescriptions = get_doc_elements(batch_invoices, med_p=True,
                                                                     with_verification_page=True, batch_file=instance)
        doc.build(elements)
        # Go to the beginning of the buffer
        buffer.seek(0)
        instance.generated_invoice_files = ContentFile(buffer.read(), 'invoice.pdf')

        merger = PdfMerger()
        for file in copies_of_medical_prescriptions:
            merger.append(file)
        pdf_buffer = BytesIO()
        merger.write(pdf_buffer)
        pdf_buffer.seek(0)
        instance.medical_prescriptions = ContentFile(pdf_buffer.read(), 'ordos.pdf')
        instance.save()
        end = datetime.now()
        if os.environ.get('LOCAL_ENV', None):
            print("Batch {0} processed in {1} seconds".format(instance, (end - start).seconds))
        else:
            url = config.ROOT_URL + 'admin/invoices/invoiceitembatch/?id=' + '{0}'.format(instance.id)
            notify_system_via_google_webhook(
                "Batch {0} processed in {1} seconds click on link to check {2}".format(instance, (end - start).seconds,
                url))


@job
def duplicate_event_for_next_day_for_several_events(events, who_created, number_of_days=1):
    """
    Duplicate the event for the next day
    @param who_created:
    @param number_of_days:
    @param events:
    @return:
    """
    start = datetime.now()
    events_created = []
    try:
        for event in events:
            next_day = event.day + timedelta(days=number_of_days)
            from invoices.events import Event
            if not Event.objects.filter(day=next_day, time_start_event=event.time_start_event,
                                        time_end_event=event.time_end_event, event_type=event.event_type,
                                        employees=event.employees, patient=event.patient).exists():
                new_event = Event.objects.create(day=next_day, time_start_event=event.time_start_event,
                                                 time_end_event=event.time_end_event,
                                                 event_type_enum=event.event_type_enum,
                                                 state=2, notes=event.notes,
                                                 employees=event.employees, patient=event.patient,
                                                 event_address=event.event_address,
                                                 created_by='duplicate_event_for_next_day')
                new_event.save()
                events_created.append(new_event)
        if events_created and len(events_created) > 0:
            # build url to the newly created events
            url = config.ROOT_URL + 'admin/invoices/eventlist/?id__in=' + ','.join(
                [str(event.id) for event in events_created])
            end = datetime.now()
            notify_system_via_google_webhook(
                "The following events were created for the day D+{0}: {1} by user {2} and it took {3} sec to generate".format(
                    number_of_days, url, who_created, (end - start).seconds))
    except Exception as e:
        error_detail = traceback.format_exc()
        notify_system_via_google_webhook(
            "*An error occurred while duplicating events for the next day: {0}*\nDetails:\n{1}".format(e, error_detail))


def update_events_address(events, address):
    """
    Update the address of the events
    @param events:
    @param address:
    @return:
    """
    start = datetime.now()
    for event in events:
        event.event_address = address
        event.save()
    end = datetime.now()
    notify_system_via_google_webhook(
        "The address of the following events was updated to {0}: {1} and it took {2} sec to generate".format(
            address, ','.join([str(event.id) for event in events]), (end - start).seconds))

@job(timeout=600)
def sync_google_contacts(employees):
    """
    Sync the google contacts for the given employees
    @param employees:
    @return:
    """
    start = datetime.now()
    try:
        for employee in employees:
            employee.sync_google_contacts()
        end = datetime.now()
        notify_system_via_google_webhook(
            "The google contacts of the following employees were synced: {0} and it took {1} sec to generate".format(
                ','.join([str(employee) for employee in employees]), (end - start).seconds))
    except Exception as e:
        error_detail = traceback.format_exc()
        notify_system_via_google_webhook(
            "*An error occurred while syncing google contacts: {0}*\nDetails:\n{1}".format(e, error_detail))
