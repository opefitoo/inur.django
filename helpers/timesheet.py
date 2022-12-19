import calendar
from datetime import datetime, timedelta
from typing import Any, Union

import holidays
from django.db.models import Q
from django.utils import timezone

from helpers.models import SicknessHolidayDaysCalculations, TotalTimesheetCalculations
from invoices.employee import Employee
from invoices.enums.generic import HolidayRequestChoice
from invoices.enums.holidays import HolidayRequestWorkflowStatus
from invoices.holidays import HolidayRequest


def display_in_hours_minutes_value(total_seconds):
    return "%d h:%d mn" % (total_seconds // 3600, (total_seconds % 3600) // 60)


def how_many_working_days_in_range(start_date):
    lu_holidays = holidays.Luxembourg()
    days = 0
    for i in range(0, calendar.monthrange(start_date.year, start_date.month)[1]):
        next_date = start_date + timedelta(i)
        if next_date.weekday() not in (5, 6) and next_date not in lu_holidays:
            days = days + 1
    return days


def absence_hours_taken(simplified_timesheet_object):
    data = {'start_date': simplified_timesheet_object.get_start_date,
            'end_date': simplified_timesheet_object.get_end_date,
            'user_id': simplified_timesheet_object.user.id}
    holiday_requests = HolidayRequest.objects.filter(
        Q(start_date__range=(data['start_date'], data['end_date'])) |
        Q(end_date__range=(data['start_date'], data['end_date'])) |
        Q(start_date__lte=data['start_date'], end_date__gte=data['start_date']) |
        Q(start_date__lte=data['end_date'], end_date__gte=data['end_date'])
    ).filter(employee_id=data['user_id']).filter(request_status=HolidayRequestWorkflowStatus.ACCEPTED).filter(
        reason__in=[1, 2, 5])
    lu_holidays = holidays.Luxembourg()
    sh_object = SicknessHolidayDaysCalculations(holidays_count=0,
                                                sickness_days_count=0,
                                                exceptional_break=0,
                                                number_of_public_holidays=0,
                                                daily_working_hours=0,

                                                holiday_sickness_requests_dates=holiday_requests)
    counter = 0
    counter_sickness = 0
    counter_exceptional_break = 0
    if len(holiday_requests) > 0:
        for holiday_request in holiday_requests:
            if holiday_request.start_date == holiday_request.end_date:
                delta = 1
                my_date = holiday_request.start_date
            else:
                if holiday_request.end_date > data['end_date'].date():
                    period_end_date = data['end_date'].date()
                else:
                    period_end_date = holiday_request.end_date
                if holiday_request.start_date < data['start_date'].date():
                    period_start_date = data['start_date'].date()
                else:
                    period_start_date = holiday_request.start_date
                delta = period_end_date - period_start_date
                my_date = period_start_date
            if holiday_request.reason == 1:
                for _ in (range(1) if delta == 1 else range(delta.days)):
                    if my_date in lu_holidays:
                        pass
                    else:
                        if my_date.weekday() < 5 and holiday_request.requested_period != HolidayRequestChoice.req_full_day:
                            counter += 0.5
                        elif my_date.weekday() < 5 and holiday_request.requested_period == HolidayRequestChoice.req_full_day:
                            counter += 1
                    my_date = my_date + timedelta(days=1)

            elif holiday_request.reason == 2:
                for _ in (range(1) if delta == 1 else range(delta.days)):
                    if my_date in lu_holidays:
                        pass
                    else:
                        if my_date.weekday() < 5 and holiday_request.requested_period != HolidayRequestChoice.req_full_day:
                            counter_sickness += 0.5
                        elif my_date.weekday() < 5 and holiday_request.requested_period == HolidayRequestChoice.req_full_day:
                            counter_sickness += 1
                    my_date = my_date + timedelta(days=1)
            elif holiday_request.reason == 5:
                for _ in (range(1) if delta == 1 else range(delta.days)):
                    if my_date in lu_holidays:
                        pass
                    else:
                        if my_date.weekday() < 5 and holiday_request.requested_period != HolidayRequestChoice.req_full_day:
                            counter_exceptional_break += 0.5
                        elif my_date.weekday() < 5 and holiday_request.requested_period == HolidayRequestChoice.req_full_day:
                            counter_exceptional_break += 1
                    my_date = my_date + timedelta(days=1)

        number_of_public_holidays = 0

        heures_jour = Employee.objects.get(user_id=data['user_id']).employeecontractdetail_set.filter(Q(
            end_date__gte=data['end_date'], start_date__lte=data['start_date']) | Q(
            end_date__isnull=True,
            start_date__lte=data['start_date'])).first().number_of_hours / 5
        # FIXME replace here
        current_month_holidays = lu_holidays[
                                 simplified_timesheet_object.get_start_date: simplified_timesheet_object.get_end_date]
        for public_holiday in current_month_holidays:
            if datetime(public_holiday.year, public_holiday.month, public_holiday.day).weekday() < 5:
                number_of_public_holidays = number_of_public_holidays + 1

        counter_sickness = counter_sickness
        sh_object.holidays_count = counter
        sh_object.sickness_days_count = counter_sickness
        sh_object.exceptional_break = counter_exceptional_break
        sh_object.number_of_public_holidays = number_of_public_holidays
        sh_object.daily_working_hours = heures_jour
        sh_object.public_holidays = current_month_holidays
    return sh_object


def hours_should_work_gross_in_sec(simplified_timesheet_object):
    calculated_hours = calculate_total_hours(simplified_timesheet_object)
    balance: Union[float, Any] = calculated_hours.total_hours.total_seconds() \
                                 + (calculated_hours.total_hours_holidays_absence_taken
                                    - calculated_hours.total_legal_working_hours) * 3600
    return balance


def calculate_total_hours(simplified_timesheet_object):
    format_data = "%d/%m/%Y"

    lu_holidays = holidays.Luxembourg()
    total = timezone.timedelta(0)
    total_sundays = timezone.timedelta(0)
    total_public_holidays = timezone.timedelta(0)
    sundays = []
    public_holidays = []
    for v in simplified_timesheet_object.simplifiedtimesheetdetail_set.all():
        total = total + v.time_delta()
        if v.start_date.astimezone().weekday() == 6:
            total_sundays = total_sundays + v.time_delta()
            sundays.append(datetime.strftime(v.start_date, format_data))
        if v.start_date in lu_holidays:
            total_public_holidays = total_public_holidays + v.time_delta()
            public_holidays.append(datetime.strftime(v.start_date, format_data))
    sh_object = absence_hours_taken(simplified_timesheet_object)
    total_legal_working_hours = how_many_working_days_in_range(simplified_timesheet_object.get_start_date) * \
                                ((simplified_timesheet_object.employee.employeecontractdetail_set.filter(Q(
                                    end_date__gte=simplified_timesheet_object.get_end_date,
                                    start_date__lte=simplified_timesheet_object.get_start_date) | Q(
                                    end_date__isnull=True,
                                    start_date__lte=simplified_timesheet_object.get_start_date)).first().number_of_hours / 5))
    calculations_object = TotalTimesheetCalculations(total_hours=total,
                                                     total_sundays=total_sundays,
                                                     total_hours_during_public_holidays=total_public_holidays,
                                                     total_hours_holidays_absence_taken=sh_object.compute_total_hours(),
                                                     total_hours_holidays_absence_taken_object=sh_object,
                                                     total_legal_working_hours=total_legal_working_hours)
    calculations_object.list_of_sundays_worked = sundays
    calculations_object.list_of_public_holidays_worked = public_holidays

    return calculations_object


def build_use_case_objects(queryset):
    _counter = 1
    file_data = ""
    for tsheet in queryset:
        # take previous months timesheet
        for v in tsheet.simplifiedtimesheetdetail_set.all():
            file_data += "\nSimplifiedTimesheetDetail.objects.create(" + \
                         "\nstart_date=timezone.now().replace(year=%s, month=%s, day=%s, hour=%s, minute=%s," % (
                             v.start_date.year, v.start_date.month, v.start_date.day, v.start_date.hour,
                             v.start_date.minute)
            file_data += "\nsecond=0, microsecond=0),"
            file_data += "\nend_date=timezone.now().replace(year=%s, month=%s, day=%s, hour=%s, minute=%s," % (
                v.start_date.year, v.start_date.month, v.start_date.day, v.end_date.hour, v.end_date.minute)
            file_data += "\nsecond=0, microsecond=0), simplified_timesheet=simplified_timesheet)"
    return file_data
