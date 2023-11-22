import calendar
from datetime import datetime, timezone, date

from django.db import transaction
from django.db.models import Q

from dependence.activity import LongTermMonthlyActivityDetail, LongTermMonthlyActivity
from dependence.detailedcareplan import get_summaries_between_two_dates
from dependence.invoicing import LongTermCareMonthlyStatement, LongTermCareInvoiceFile, LongTermCareInvoiceLine, \
    LongTermCareInvoiceItem
# LongTermCareInvoiceItem
from dependence.longtermcareitem import LongTermPackage, LongTermCareItem
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
    statement = create_monthly_invoice(patients, 3, 2023)

@transaction.atomic
def create_assurance_dependance_invoices_june_2023(self, request, queryset):
    """
    Create AEV invoices for all patients for the month of March 2023
    """
    # get all patients
    # exit date based on timezones
    start_period = datetime(2023, 6, 1, tzinfo=timezone.utc)
    # either less or equal to end period or null
    patients = Patient.objects.filter(is_under_dependence_insurance=True).filter(
        Q(date_of_exit__gte=start_period) | Q(date_of_exit__isnull=True)).filter(Q(date_of_death__gte=start_period) | Q(date_of_death__isnull=True))
    # create invoices for each patient
    statement = create_monthly_invoice(patients, 6, 2023)

@transaction.atomic
def create_assurance_dependance_invoices_july_2023(self, request, queryset):
    """
    Create AEV invoices for all patients for the month of March 2023
    """
    # get all patients
    # exit date based on timezones
    start_period = datetime(2023, 7, 1, tzinfo=timezone.utc)
    # either less or equal to end period or null
    patients = Patient.objects.filter(is_under_dependence_insurance=True).filter(
        Q(date_of_exit__gte=start_period) | Q(date_of_exit__isnull=True)).filter(Q(date_of_death__gte=start_period) | Q(date_of_death__isnull=True))
    # create invoices for each patient
    statement = create_monthly_invoice(patients, 7, 2023)
@transaction.atomic
def create_assurance_dependance_invoices_june_selected_patient_2023(self, request, queryset):
    """
    Create AEV invoices for all patients for the month of March 2023
    """
    # get all patients
    # exit date based on timezones
    start_period = datetime(2023, 6, 1, tzinfo=timezone.utc)
    medical_care_summary_per_patient_objects = queryset.all()

    # Retrieve the patients from the selected MedicalCareSummaryPerPatient objects
    selected_patients = [mcspp.patient for mcspp in medical_care_summary_per_patient_objects]

    statement = create_monthly_invoice(selected_patients, 6, 2023)
    # display admin message
    self.message_user(request, "Factures AEV créées pour les patients sélectionnés {}".format(statement))

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
        create_monthly_invoice_line_v2(patient, statement, month=month, year=year)
        create_monthly_invoice_items(patient, statement, month=month, year=year)
    return statement


def create_packages(invoice, start_period, end_period, long_term_package):
    return LongTermCareInvoiceLine.objects.get_or_create(invoice=invoice,
                                                         start_period=start_period,
                                                         end_period=end_period,
                                                         long_term_care_package=long_term_package)




def create_monthly_invoice_line_v2(patient, statement, month, year):
    start_period = date(year, month, 1)
    # end period is last day of the month
    last_day = calendar.monthrange(year, month)[1]
    end_period = date(year, month, last_day)
    invoice, created = LongTermCareInvoiceFile.objects.get_or_create(link_to_monthly_statement=statement,
                                                                     patient=patient,
                                                                     invoice_start_period=start_period,
                                                                     invoice_end_period=end_period)
    if LongTermMonthlyActivity.objects.filter(patient=patient, year=start_period.year,
                                              month=start_period.month).count() == 0:
        return invoice

    activity = LongTermMonthlyActivity.objects.filter(patient=patient, year=start_period.year,
                                                      month=start_period.month).get()
    first_day = activity.get_first_date_for_activity_detail()
    last_day = activity.get_last_date_for_activity_detail()
    summaries = get_summaries_between_two_dates(patient, first_day, last_day)
    for summary in summaries:
        if summary.medicalSummaryPerPatient.special_package is not None and summary.medicalSummaryPerPatient.level_of_needs == 780:
            # create an invoice line for each activity
            forfait_soins_palliatifs_long_term_package = LongTermPackage.objects.filter(code="AEVFSP").get()
            create_packages(invoice, summary.start_date, summary.end_date, forfait_soins_palliatifs_long_term_package)
        elif summary.medicalSummaryPerPatient.nature_package is not None:
            aev_long_term_package = LongTermPackage.objects.filter(
                dependence_level=summary.medicalSummaryPerPatient.nature_package).get()
            create_packages(invoice, summary.start_date, summary.end_date, aev_long_term_package)
        elif summary.medicalSummaryPerPatient.nature_package is None:
            aev_long_term_package = LongTermPackage.objects.filter(
                dependence_level=summary.medicalSummaryPerPatient.level_of_needs).get()
            create_packages(invoice, summary.start_date, summary.end_date, aev_long_term_package)
        amdm_activity_item = LongTermCareItem.objects.filter(code="AMD-M").get()
        if activity.how_many_occurrence_of_activity(amdm_activity_item, first_day, last_day) > 0:
            # create an invoice line for each activity
            amdm_long_term_package = LongTermPackage.objects.filter(code="FAMDM").get()
            create_packages(invoice, summary.start_date, summary.end_date, amdm_long_term_package)
    return invoice


def create_monthly_invoice_items(patient, statement, month, year):
    start_period = date(year, month, 1)
    # end period is last day of the month
    last_day = calendar.monthrange(year, month)[1]
    end_period = date(year, month, last_day)
    invoice, created = LongTermCareInvoiceFile.objects.get_or_create(link_to_monthly_statement=statement,
                                                                     patient=patient,
                                                                     invoice_start_period=start_period,
                                                                     invoice_end_period=end_period)
    if LongTermMonthlyActivity.objects.filter(patient=patient, year=start_period.year,
                                              month=start_period.month).count() == 0:
        return invoice
    long_term_monthly_activity = LongTermMonthlyActivity.objects.filter(patient=patient, year=start_period.year,
                                                                        month=start_period.month).get()
    dtls = LongTermMonthlyActivityDetail.objects.filter(long_term_monthly_activity=long_term_monthly_activity).order_by(
        'activity_date')
    for dtl in dtls:
        if "AMD-GI" == dtl.activity.code:
            print(dtl.activity.code + " " + str(dtl.activity_date) + " " + str(dtl.quantity) + " " + str(patient))
            # create as many invoice items as quantity
            LongTermCareInvoiceItem.objects.create(invoice=invoice,
                                                       care_date=dtl.activity_date,
                                                       long_term_care_package=LongTermPackage.objects.filter(
                                                           code="AMDGI").get(),
                                                       quantity=dtl.quantity * 2)
        elif "AAI" == dtl.activity.code:
            print(dtl.activity.code + " " + str(dtl.activity_date) + " " + str(dtl.quantity))
            # create as many invoice items as quantity
            invoice_item = LongTermCareInvoiceItem.objects.create(invoice=invoice,
                                                                      care_date=dtl.activity_date,
                                                                      long_term_care_package=LongTermPackage.objects.filter(
                                                                          code="AAII").get(),
                                                                      quantity=dtl.quantity * 2)


