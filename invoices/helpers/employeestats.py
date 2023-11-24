from invoices.employee import Employee


def list_all_active_employees():
    return Employee.objects.filter(end_contract__isnull=True).order_by('-id')

def list_all_active_contracts():
    all_active_employees = list_all_active_employees()
    all_active_contracts = []
    for employee in all_active_employees:
        all_active_contracts.append(employee.get_current_contract())
    return all_active_contracts
