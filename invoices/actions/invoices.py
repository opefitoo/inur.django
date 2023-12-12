import calendar
from datetime import date, timedelta

from django.core.checks import messages
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from invoices.employee import Employee, JobPosition
from invoices.events import Event
from invoices.models import Prestation, InvoiceItem, CareCode, Hospitalization
from invoices.modelspackage import InvoicingDetails


@transaction.atomic
def generer_forfait_aev_mars(self, request, queryset):
    # only for superuser
    if not request.user.is_superuser:
        return
    final_result = []
    for patient in queryset:
        if patient.is_under_dependence_insurance:
            final_result.append(create_prestations_for_month_v2(patient, 2023, 3))
    if len(final_result) > 0:
        #  final_result string with list of invoice numbers
        invoice_numbers = ", ".join([str(x) for x in final_result])
        self.message_user(request, "Forfait AEV MARS généré avec succès %s factures générées %s" % (
            len(final_result), invoice_numbers),
                          level=messages.INFO)
    else:
        self.message_user(request, "BUG", level=messages.ERROR)

@transaction.atomic
def generer_forfait_aev_avril(self, request, queryset):
    # only for superuser
    if not request.user.is_superuser:
        return
    final_result = []
    for patient in queryset:
        if patient.is_under_dependence_insurance:
            final_result.append(create_prestations_for_month_v2(patient, 2023, 4))
    if len(final_result) > 0:
        #  final_result string with list of invoice numbers
        invoice_numbers = ", ".join([str(x) for x in final_result])
        self.message_user(request, "Forfait AEV AVRIL généré avec succès %s factures générées %s" % (
            len(final_result), invoice_numbers),
                          level=messages.INFO)
    else:
        self.message_user(request, "BUG", level=messages.ERROR)

@transaction.atomic
def generer_forfait_aev_mai(self, request, queryset):
    # only for superuser
    if not request.user.is_superuser:
        return
    final_result = []
    for patient in queryset:
        if patient.is_under_dependence_insurance:
            final_result.append(create_prestations_for_month_v2(patient, 2023, 5))
    if len(final_result) > 0:
        #  final_result string with list of invoice numbers
        invoice_numbers = ", ".join([str(x) for x in final_result])
        self.message_user(request, "Forfait AEV Mai généré avec succès %s factures générées %s" % (
            len(final_result), invoice_numbers),
                          level=messages.INFO)
    else:
        self.message_user(request, "BUG", level=messages.ERROR)

@transaction.atomic
def generer_forfait_aev_june(self, request, queryset):
    # only for superuser
    if not request.user.is_superuser:
        return
    final_result = []
    for patient in queryset:
        if patient.is_under_dependence_insurance:
            final_result.append(create_prestations_for_month_v2(patient, 2023, 6))
    if len(final_result) > 0:
        #  final_result string with list of invoice numbers
        invoice_numbers = ", ".join([str(x) for x in final_result])
        self.message_user(request, "Forfait AEV Juin généré avec succès %s factures générées %s" % (
            len(final_result), invoice_numbers),
                          level=messages.INFO)
    else:
        self.message_user(request, "BUG", level=messages.ERROR)

@transaction.atomic
def generer_forfait_aev_july(self, request, queryset):
    # only for superuser
    if not request.user.is_superuser:
        return
    final_result = []
    for patient in queryset:
        if patient.is_under_dependence_insurance:
            final_result.append(create_prestations_for_month_v2(patient, 2023, 7))
    if len(final_result) > 0:
        #  final_result string with list of invoice numbers
        invoice_numbers = ", ".join([str(x) for x in final_result])
        self.message_user(request, "Forfait AEV Juin généré avec succès %s factures générées %s" % (
            len(final_result), invoice_numbers),
                          level=messages.INFO)
    else:
        self.message_user(request, "BUG", level=messages.ERROR)

@transaction.atomic
def generer_forfait_aev_august(self, request, queryset):
    # only for superuser
    if not request.user.is_superuser:
        return
    final_result = []
    for patient in queryset:
        if patient.is_under_dependence_insurance:
            final_result.append(create_prestations_for_month_v2(patient, 2023, 8))
    if len(final_result) > 0:
        #  final_result string with list of invoice numbers
        invoice_numbers = ", ".join([str(x) for x in final_result])
        self.message_user(request, "Forfait AEV Aout généré avec succès %s factures générées %s" % (
            len(final_result), invoice_numbers),
                          level=messages.INFO)
    else:
        self.message_user(request, "BUG", level=messages.ERROR)

@transaction.atomic
def generer_forfait_aev_september(self, request, queryset):
    # only for superuser
    if not request.user.is_superuser:
        return
    final_result = []
    for patient in queryset:
        if patient.is_under_dependence_insurance:
            final_result.append(create_prestations_for_month_v2(patient, 2023, 9))
    if len(final_result) > 0:
        #  final_result string with list of invoice numbers
        invoice_numbers = ", ".join([str(x) for x in final_result])
        self.message_user(request, "Forfait AEV Septembre généré avec succès %s factures générées %s" % (
            len(final_result), invoice_numbers),
                          level=messages.INFO)
    else:
        self.message_user(request, "BUG", level=messages.ERROR)


@transaction.atomic
def generer_forfait_aev_octobre(self, request, queryset):
    # only for superuser
    if not request.user.is_superuser:
        return
    final_result = []
    for patient in queryset:
        if patient.is_under_dependence_insurance:
            final_result.append(create_prestations_for_month_v2(patient, 2023, 10))
    if len(final_result) > 0:
        #  final_result string with list of invoice numbers
        invoice_numbers = ", ".join([str(x) for x in final_result])
        self.message_user(request, "Forfait AEV Octobre généré avec succès %s factures générées %s" % (
            len(final_result), invoice_numbers),
                          level=messages.INFO)
    else:
        self.message_user(request, "BUG", level=messages.ERROR)

def create_prestations_for_month_v2(patient, year, month):
    infi_job_position = JobPosition.objects.filter(name__istartswith="infi").get()
    employees_id = Employee.objects.filter(Q(occupation=infi_job_position) | Q(id=1)).all().values_list('id',
                                                                                                        flat=True)
    events = Event.objects.filter(patient=patient, day__month=month, day__year=year,
                                  state__in=[Event.STATES[2][0],
                                             Event.STATES[3][0]],
                                  employees_id__in=employees_id)
    events_made_by_non_nurse = Event.objects.filter(patient=patient, day__month=month, day__year=year,
                                                    state__in=[Event.STATES[2][0],
                                                               Event.STATES[3][0]])
    days_in_month = calendar.monthrange(year, month)[1]
    # prestation_date = datetime(year, month, 1, 8, 0)
    prestation_date = timezone.now().replace(year=year, month=month, day=1, hour=8, minute=0,
                                             tzinfo=None)
    prestations = []
    for day in range(1, days_in_month + 1):
        if patient.date_of_exit and patient.date_of_exit < prestation_date.date():
            print("Patient %s is out on this date %s" % (patient, prestation_date))
            break
        if patient.date_of_death and patient.date_of_death < prestation_date.date():
            print("Patient %s is dead on this date %s" % (patient, prestation_date))
            break
        hospitalizations = Hospitalization.objects.filter(
            patient=patient,
            start_date__lte=prestation_date
        ).filter(
            Q(end_date__gt=prestation_date) | Q(end_date__isnull=True)
        )
        if 0 == hospitalizations.count():
            # Choose the invoice based on the current day (0-indexed)
            if events.filter(day__day=day).count() > 0:
                prestations.append(Prestation(date=prestation_date,
                                              employee=events.filter(day__day=day).first().employees,
                                              carecode=CareCode.objects.get(code='N803')))
            elif events_made_by_non_nurse.filter(day__day=day).count() > 0:
                prestations.append(Prestation(date=prestation_date,
                                              employee=Employee.objects.get(id=1),
                                              carecode=CareCode.objects.get(code='N803')))
            else:
                prestations.append(Prestation(date=prestation_date,
                                              employee=Employee.objects.get(id=1),
                                              carecode=CareCode.objects.get(code='N803')))
                print("no event for day %s for patient %s but adding one as no hospi." % (day, patient))
        prestation_date += timedelta(days=1)

    # every 20 prestations we create an invoice
    invoices = []
    for i in range(0, len(prestations), 20):
        invoice_item = InvoiceItem.objects.create(patient=patient,
                                                  # invoice date is last day of the month
                                                  invoice_date=date(year, month, days_in_month),
                                                  invoice_send_date=timezone.now(),
                                                  created_by="script_assurance_dependance",
                                                  invoice_details=InvoicingDetails.objects.filter(
                                                      default_invoicing=True).get())
        # loop over the prestations and add them to the invoice
        for prestation in prestations[i:i + 20]:
            prestation.invoice_item = invoice_item
            prestation.save()
        invoices.append(invoice_item)
    return invoices
