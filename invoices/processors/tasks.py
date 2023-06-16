from io import BytesIO

from PyPDF2 import PdfMerger
from django.core.files.base import ContentFile
from django.db.models import Q
from django_rq import job
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate

from invoices.enums.generic import BatchTypeChoices
from invoices.invoiceitem_pdf import get_doc_elements
from invoices.notifications import notify_system_via_google_webhook
from invoices.prefac import generate_all_invoice_lines


@job
def process_post_save(instance):
    # calculate how much time it takes to process the batch
    from datetime import datetime
    start = datetime.now()
    _must_update = False

    if instance.force_update:
        _must_update = True
        instance.version += 1
        instance.force_update = False
    if _must_update:
        # Now update all InvoiceItems which have an invoice_date within this range
        from invoices.models import InvoiceItem
        batch_invoices = InvoiceItem.objects.filter(
            Q(invoice_date__gte=instance.start_date) & Q(invoice_date__lte=instance.end_date)).filter(
            invoice_sent=False)
        if BatchTypeChoices.CNS_INF == instance.batch_type:
            batch_invoices.update(batch=instance)
            file_content = generate_all_invoice_lines(batch_invoices, sending_date=instance.send_date),
            instance.prefac_file = ContentFile(file_content[0].encode('utf-8'), 'prefac.txt')

            # generate the pdf invoice file
            # Create a BytesIO buffer
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, rightMargin=2 * cm, leftMargin=2 * cm, topMargin=1 * cm,
                                    bottomMargin=1 * cm)
            elements, copies_of_medical_prescriptions = get_doc_elements(batch_invoices, med_p=True,
                                                                         with_verification_page=True)
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
            notify_system_via_google_webhook("Batch {0} processed in {1} seconds".format(instance, (end - start).seconds))
