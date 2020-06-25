from django.db.models import Q

from invoices.employee import Employee, EmployeeContractDetail
from invoices.holidays import HolidayRequest


def how_many_hours_taken_in_period(data):
    holiday_requests = HolidayRequest.objects.filter(
        Q(start_date__range=(data['start_date'], data['end_date'])) |
        Q(end_date__range=(data['start_date'], data['end_date'])) |
        Q(start_date__lte=data['start_date'], end_date__gte=data['start_date']) |
        Q(start_date__lte=data['end_date'], end_date__gte=data['end_date'])
    ).filter(employee_id=data['user_id']).filter(request_accepted=True)
    if len(holiday_requests) > 0:
        return len(holiday_requests) * Employee.objects.get(user_id=data['user_id']).employeecontractdetail_set.filter(
            start_date__lte=data['start_date']).first().number_of_hours / 5
    return 0
