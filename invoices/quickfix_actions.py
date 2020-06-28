# -*- coding: utf-8 -*-
from django.contrib import messages

from invoices.models import InvoiceItem, Prestation
from invoices.models.employee import Employee


def set_employee_for_invoice(modeladmin, request, queryset):
    # Create the HttpResponse object with the appropriate PDF headers.
    invoices: InvoiceItem
    counter = 0
    for invoices in queryset:
        queryset = invoices.prestations.all()
        prestation: Prestation
        for prestation in queryset:
            print(prestation)
            if prestation.employee is None:
                prestation.employee = Employee.objects.get(id=1)
                prestation.save()
                counter = counter +1
    messages.success(request, 'Success for %d' % counter)


set_employee_for_invoice.short_description = "Set Employee"
