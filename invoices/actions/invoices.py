import calendar
from datetime import date, timedelta

from django.core.checks import messages
from django.db.models import Q
from django.utils import timezone

from invoices.employee import Employee
from invoices.events import Event
from invoices.models import Prestation, InvoiceItem, CareCode, Hospitalization


def generer_forfait_aev_mars(self, request, queryset):
    # only for superuser
    if not request.user.is_superuser:
        return
    for patient in queryset:
        if patient.is_under_dependence_insurance:
            result = create_prestations_for_month(patient, 2023, 3)
    if result:
        #  build string with list of invoice numbers
        invoice_numbers = ', '.join([str(invoice.invoice_number) for invoice in result])
        self.message_user(request, "Forfait AEV MARS généré avec succès %s factures générées %s"  % (len(result), invoice_numbers),
                          level=messages.INFO)
    else:
        self.message_user(request, "BUG", level=messages.ERROR)


def create_prestations_for_month(patient, year, month):
    # Calculate the total number of days in the month
    days_in_month = calendar.monthrange(year, month)[1]

    # Calculate the number of invoices needed to accommodate the prestations
    num_invoices = (days_in_month + 19) // 20

    # Create the invoices

    invoices = [InvoiceItem.objects.create(patient=patient,
                                           # invoice date is last day of the month
                                           invoice_date=date(year, month, days_in_month),
                                           invoice_send_date=timezone.now()
                                           ) for _ in range(num_invoices)]

    # Generate prestations for every day of the month
    prestation_date = timezone.now().replace(year=year, month=month, day=1, hour=8, minute=0)
    # prestation_date = datetime(year, month, 1, 8, 0)
    for day in range(days_in_month):
        events = Event.objects.filter(patient=patient, day=prestation_date, state__in=[Event.STATES[2][0],
                                                                                       Event.STATES[3][0]])
        hospitalizations = Hospitalization.objects.filter(
            patient=patient,
            start_date__lte=prestation_date
        ).filter(
            Q(end_date__gt=prestation_date) | Q(end_date__isnull=True)
        )
        if events.count() > 0 and hospitalizations.count() == 0:
            # Choose the invoice based on the current day (0-indexed)
            invoice = invoices[day // 20]
            Prestation.objects.create(invoice_item=invoice, date=prestation_date,
                                      employee=Employee.objects.get(user_id=1),
                                      carecode=CareCode.objects.get(code='N803'), at_home=False)
            prestation_date += timedelta(days=1)
    invoices_kept = []
    for invoice in invoices:
        if invoice.number_of_prestations == 0:
            invoice.delete()
        else:
            invoices_kept.append(invoice)
    return invoices_kept
