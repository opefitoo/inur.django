from datetime import timedelta

from django.db.models import Q

from invoices.employee import Employee
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
        counter = 0
        for holiday_request in holiday_requests:
            delta = holiday_request.end_date - holiday_request.start_date
            date = holiday_request.start_date
            for i in range(delta.days):
                if date.weekday() < 5:
                    counter += 1
                date = date + timedelta(days=1)
            number_of_public_holidays = 0
            for public_holiday in public_holidays:
                if public_holiday.calendar_date.weekday() < 5:
                    number_of_public_holidays = number_of_public_holidays + 1
            counter = counter - number_of_public_holidays
        heures_jour = Employee.objects.get(user_id=data['user_id']).employeecontractdetail_set.filter(
            start_date__lte=data['start_date']).first().number_of_hours / 5
        return [(counter - number_of_public_holidays) * heures_jour,
                "explication: ( %d jours congés - %d jours fériés )  x %d nombre h. /j" % (counter,
                                                                                           number_of_public_holidays,
                                                                                           heures_jour)]
    return [0, ""]


def whois_off(day_off):
    reqs = HolidayRequest.objects.filter(request_status=HolidayRequestWorkflowStatus.ACCEPTED,
                                         start_date__lte=day_off, end_date__gte=day_off)
    employees_abbreviations = ""
    for r in reqs:
        employees_abbreviations += r.employee.employee.abbreviation + ","
    return employees_abbreviations[:-1]
