from datetime import datetime

from django.db.models import Q

from invoices.employee import Employee


def get_admin_emails():
    admin_emails = []
    for em in Employee.objects.filter(occupation__name='administratrice'):
        admin_emails.append(em.user.email)
    return admin_emails


def get_pks_all_active_employees():
    pks = ""
    employee_ids = Employee.objects.filter(
        Q(end_contract__gt=datetime.now()) | Q(end_contract__isnull=True)).values_list(
        'id', flat=True)
    for d in employee_ids:
        pks.append(d)
        pks.append(",")
    return pks


def get_employee_id_by_abbreviation(abr):
    return Employee.objects.get(abbreviation=abr).id
