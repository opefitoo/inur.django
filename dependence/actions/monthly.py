import calendar
from datetime import datetime, timezone

from django.db import transaction
from django.db.models import Q

from dependence.detailedcareplan import MedicalCareSummaryPerPatient
from dependence.invoicing import LongTermCareMonthlyStatement, LongTermCareInvoiceFile, LongTermCareInvoiceLine
from dependence.longtermcareitem import LongTermPackage
from invoices.models import Patient


@transaction.atomic
def create_aev_invoices_mars_2023(self, request, queryset):
    """
    Create AEV invoices for all patients for the month of March 2023
    """
    # get all patients
    # exit date based on timezones
    end_period = datetime(2023, 3, 31, tzinfo=timezone.utc)
    # either less or equal to end period or null
    patients = Patient.objects.filter(is_under_dependence_insurance=True).filter(
        Q(date_of_exit__lte=end_period) | Q(date_of_exit__isnull=True))
    # create invoices for each patient
    for patient in patients:
        create_monthly_invoice(patient, 3, 2023)


def create_monthly_invoice(patient_list, month, year):
    """
    Create a monthly invoice for a patient
    :param patient_list: list of patients
    :param month: int
    :param year: int
    :return: LongTermCareMonthlyStatement
    """
    # get all activities for this patient for this month
    # activities = LongTermCareActivity.objects.filter(patient=patient, date__month=month, date__year=year)
    # create a new invoice
    statement, created = LongTermCareMonthlyStatement.objects.get_or_create(month=month, year=year)
    for patient in patient_list:
        create_monthly_invoice_line(patient, statement, month=month, year=year)
    return statement


def create_monthly_invoice_line(patient, statement, month, year):
    # first day of the month
    start_period = datetime(year, month, 1)
    # end period is last day of the month
    last_day = calendar.monthrange(year, month)[1]
    end_period = datetime(year, month, last_day)
    summaries = MedicalCareSummaryPerPatient.objects.filter(patient=patient,
                                                            date_of_decision__lte=start_period)
    if summaries.count() != 0:
        # create an invoice line for each activity
        invoice, created = LongTermCareInvoiceFile.objects.get_or_create(link_to_monthly_statement=statement,
                                                                         patient=patient,
                                                                         invoice_start_period=start_period,
                                                                         invoice_end_period=end_period)
        for summary in summaries:
            # look for level_of_needs
            level_of_needs = summary.level_of_needs
            long_term_package = LongTermPackage.objects.filter(dependence_level=level_of_needs).get()
            # create an invoice line for each activity
            if summary.date_of_change_to_new_plan is not None:
                end_period = summary.date_of_change_to_new_plan
                start_period = summary.date_of_decision
            line_aev = LongTermCareInvoiceLine.objects.get_or_create(invoice=invoice,
                                                                     start_period=start_period,
                                                                     end_period=end_period,
                                                                     long_term_care_package=long_term_package)
            line_famdm = LongTermCareInvoiceLine.objects.get_or_create(invoice=invoice,
                                                                       start_period=start_period,
                                                                       end_period=end_period,
                                                                       long_term_care_package=LongTermPackage.objects.filter(
                                                                           code='FAMDM').get())

            line_gardes = LongTermCareInvoiceLine.objects.get_or_create(invoice=invoice,
                                                                        start_period=start_period,
                                                                        end_period=end_period,
                                                                        long_term_care_package=LongTermPackage.objects.filter(
                                                                            code='AMDGI').get())

        return invoice
