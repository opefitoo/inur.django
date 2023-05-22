import calendar
from datetime import datetime, timezone, timedelta, date

from django.db import transaction
from django.db.models import Q

from dependence.activity import LongTermMonthlyActivityDetail, LongTermMonthlyActivity
from dependence.detailedcareplan import MedicalCareSummaryPerPatient, get_summaries_between_two_dates
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
    self.messages.success(request, "Invoices created successfully %s" % statement)


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


def create_items(invoice, start_period, end_period, long_term_care_item):
    # loop through all days of the start period and end period
    # create an invoice item for each day
    for day in range((end_period - start_period).days + 1):
        start_period = start_period + timedelta(days=day)
        return LongTermCareInvoiceItem.objects.get_or_create(invoice=invoice,
                                                             care_date=start_period,
                                                             long_term_care_package=long_term_care_item)


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
            for i in range(dtl.quantity * 2):
                LongTermCareInvoiceItem.objects.create(invoice=invoice,
                                                              care_date=dtl.activity_date,
                                                              long_term_care_package=LongTermPackage.objects.filter(
                                                                  code="AMDGI").get())
        elif "AAI" == dtl.activity.code:
            print(dtl.activity.code + " " + str(dtl.activity_date) + " " + str(dtl.quantity))
            # create as many invoice items as quantity
            for i in range(dtl.quantity * 2):
                invoice_item = LongTermCareInvoiceItem.objects.create(invoice=invoice,
                                                              care_date=dtl.activity_date,
                                                              long_term_care_package=LongTermPackage.objects.filter(
                                                                  code="AAII").get())
                print(invoice_item)


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
            nature_package = summary.nature_package
            if nature_package is None:
                raise Exception('No nature package found for this summary')
            aev_long_term_package = LongTermPackage.objects.filter(dependence_level=nature_package).get()
            # create an invoice line for each activity
            if summary.date_of_change_to_new_plan is not None:
                end_period = summary.date_of_change_to_new_plan
                start_period = summary.date_of_decision
                # for each of period check if LongTermMonthlyActivityDetail.did_activity_happen is true
            activity = LongTermMonthlyActivity.objects.filter(patient=patient, year=start_period.year,
                                                              month=start_period.month).get()
            first_date = activity.get_first_date_for_activity_detail()
            last_day = activity.get_last_date_for_activity_detail()
            activities = LongTermMonthlyActivityDetail.objects.filter(long_term_monthly_activity=activity,
                                                                      activity_date__gte=start_period,
                                                                      activity_date__lte=end_period).all()
            cleaning_package = activities.filter(activity=LongTermCareItem.objects.filter(code='AMD-M').get()).count()
            # if cleaning_package > 0:
            # loop through all days from first_date to last_day
            # for dt in range(first_date.day, last_day.day + 1):
            # if no Hospitalization happening this day then create an invoice item
            # if Hospitalization.filter(start_date__lte=datetime(start_period.year, start_period.month, dt),
            #                           end_date__gte=datetime(start_period.year, start_period.month, dt),
            #                           patient=patient).count() == 0:
            #     item = LongTermCareInvoiceItem.objects.get_or_create(invoice=invoice,
            #                                                               care_date=dtl.activity_date,
            #                                                               long_term_care_package=LongTermPackage.objects.filter(
            #                                                                   code='FAMDM').get())
            # for dtl in activities:
            #     if dtl.activity.code.startswith("AEV"):
            #         item_aev = LongTermCareInvoiceItem.objects.get_or_create(invoice=invoice,
            #                                                                  care_date=dtl.activity_date,
            #                                                                  long_term_care_package=aev_long_term_package)
            #     elif dtl.activity.code.startswith("AMD-M"):
            #         item_cleaning = LongTermCareInvoiceItem.objects.get_or_create(invoice=invoice,
            #                                                                       care_date=dtl.activity_date,
            #                                                                       long_term_care_package=LongTermPackage.objects.filter(
            #                                                                           code='FAMDM').get())

            line_aev = LongTermCareInvoiceLine.objects.get_or_create(invoice=invoice,
                                                                     start_period=start_period,
                                                                     end_period=end_period,
                                                                     long_term_care_package=aev_long_term_package)
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
