from datetime import timedelta

from django.db.models import Q

from helpers.models import SicknessHolidayDaysCalculations
from invoices.employee import Employee
from invoices.enums.generic import HolidayRequestChoice
from invoices.enums.holidays import HolidayRequestWorkflowStatus
from invoices.holidays import HolidayRequest


def how_many_hours_taken_in_period(data, public_holidays):
    # TODO : remove hard coded values for reason filtering
    holiday_requests = HolidayRequest.objects.filter(
        Q(start_date__range=(data['start_date'], data['end_date'])) |
        Q(end_date__range=(data['start_date'], data['end_date'])) |
        Q(start_date__lte=data['start_date'], end_date__gte=data['start_date']) |
        Q(start_date__lte=data['end_date'], end_date__gte=data['end_date'])
    ).filter(employee_id=data['user_id']).filter(request_status=HolidayRequestWorkflowStatus.ACCEPTED).filter(
        reason__range=(1, 2))
    if len(holiday_requests) > 0:
        sh_object = SicknessHolidayDaysCalculations(holidays_count=0,
                                                    sickness_days_count=0,
                                                    number_of_public_holidays=0,
                                                    daily_working_hours=0,
                                                    holiday_sickness_requests_dates=holiday_requests)
        counter = 0
        counter_sickness = 0
        for holiday_request in holiday_requests:
            if holiday_request.end_date > data['end_date'].date():
                period_end_date = data['end_date'].date()
            else:
                period_end_date = holiday_request.end_date
            if holiday_request.start_date < data['start_date'].date():
                period_start_date = data['start_date'].date()
            else:
                period_start_date = holiday_request.start_date
            delta = period_end_date - period_start_date
            date = period_start_date
            if holiday_request.reason == 1:
                for i in range(delta.days):
                    if date.weekday() < 5 and holiday_request.requested_period != HolidayRequestChoice.req_full_day:
                        counter += 0.5
                    elif date.weekday() < 5 and holiday_request.requested_period == HolidayRequestChoice.req_full_day:
                        counter += 1
                    date = date + timedelta(days=1)
                number_of_public_holidays = 0
                for public_holiday in public_holidays:
                    if public_holiday.calendar_date.weekday() < 5:
                        number_of_public_holidays = number_of_public_holidays + 1
                counter = counter - number_of_public_holidays
            elif holiday_request.reason == 2:
                for i in range(delta.days):
                    if date.weekday() < 5 and holiday_request.requested_period != HolidayRequestChoice.req_full_day:
                        counter_sickness += 0.5
                    elif date.weekday() < 5 and holiday_request.requested_period == HolidayRequestChoice.req_full_day:
                        counter_sickness += 1
                    date = date + timedelta(days=1)
                number_of_public_holidays = 0
                for public_holiday in public_holidays:
                    if public_holiday.calendar_date.weekday() < 5:
                        number_of_public_holidays = number_of_public_holidays + 1
                counter_sickness = counter_sickness - number_of_public_holidays

        heures_jour = Employee.objects.get(user_id=data['user_id']).employeecontractdetail_set.filter(Q(
            end_date__gte=data['end_date'], start_date__lte=data['start_date']) | Q(
            end_date__isnull=True,
            start_date__lte=data['start_date'])).first().number_of_hours / 5
        sh_object.holidays_count = counter
        sh_object.sickness_days_count = counter_sickness
        sh_object.number_of_public_holidays = number_of_public_holidays
        sh_object.daily_working_hours = heures_jour
        return [sh_object.compute_total_hours(),
                sh_object]
    return [0, ""]


def whois_off(day_off):
    reqs = HolidayRequest.objects.filter(request_status=HolidayRequestWorkflowStatus.ACCEPTED,
                                         start_date__lte=day_off, end_date__gte=day_off)
    employees_abbreviations = ""
    for r in reqs:
        employees_abbreviations += r.employee.employee.abbreviation + ","
    return employees_abbreviations[:-1]


def whois_available(working_day):
    employees_on_leave = [x.employee for x in
                          HolidayRequest.objects.filter(request_status=HolidayRequestWorkflowStatus.ACCEPTED,
                                                        start_date__lte=working_day, end_date__gte=working_day)]
    available_employees = [x for x in Employee.objects.filter(end_contract__isnull=True) if x not in employees_on_leave]
    return [x.abbreviation for x in available_employees]
