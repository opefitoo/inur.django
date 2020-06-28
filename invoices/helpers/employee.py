from django.apps import apps
from django.db.models import Q

import invoices.models


def get_admin_emails():
    admin_emails = []
    EmployeeModel = apps.get_model("invoices", "Employee")
    for em in EmployeeModel.objects.filter(occupation__name='administratrice'):
        admin_emails.append(em.user.email)
    return admin_emails


def all_holiday_requests(user_id):
    HolidayRequest = apps.get_model("invoices", "HolidayRequest")
    return HolidayRequest.objects.filter(employee_id=user_id).filter(request_accepted=True).filter(reason=1)


def how_many_hours_taken_in_period(data):
    holiday_requests = invoices.models.HolidayRequest.objects.filter(
        Q(start_date__range=(data['start_date'], data['end_date'])) |
        Q(end_date__range=(data['start_date'], data['end_date'])) |
        Q(start_date__lte=data['start_date'], end_date__gte=data['start_date']) |
        Q(start_date__lte=data['end_date'], end_date__gte=data['end_date'])
    ).filter(employee_id=data['user_id']).filter(request_accepted=True)
    if len(holiday_requests) > 0:
        return len(holiday_requests) * invoices.models.employee.Employee.objects.get(user_id=data['user_id']).\
            employeecontractdetail_set.filter(start_date__lte=data['start_date']).first().number_of_hours / 5
    return 0