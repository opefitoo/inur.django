from django.db.models import Q


class InvoiceItemBatchManager:
    def __init__(self):
        pass

    @staticmethod
    def update_associated_invoiceitems(batch_instance):
        InvoiceItemBatchManager.disassociate_invoiceitems(batch_instance=batch_instance)
        InvoiceItemBatchManager.associate_invoiceitems(batch_instance=batch_instance)

    @staticmethod
    def disassociate_invoiceitems(batch_instance):
        from invoices.models import InvoiceItem
        queryset = InvoiceItem.objects.filter(
            (Q(invoice_date__lte=batch_instance.start_date) | Q(invoice_date__gte=batch_instance.end_date)) & Q(
                batch=batch_instance))
        for invoiceitem in queryset:
            invoiceitem.batch = None
            invoiceitem.save()

    @staticmethod
    def associate_invoiceitems(batch_instance):
        from invoices.models import InvoiceItem
        queryset = InvoiceItem.objects.filter(
            Q(invoice_date__range=(batch_instance.start_date, batch_instance.end_date)) & Q(batch__isnull=True) & Q(
                is_private=False))
        for invoiceitem in queryset:
            invoiceitem.batch = batch_instance
            invoiceitem.save()
