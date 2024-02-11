
from django.utils import timezone

from invoices.events import Event


def get_un_validated_events(employee_id):
    # since 1 mars 2023 and before current date
    now_format = timezone.now().strftime('%Y-%m-%d')
    events = Event.objects.filter(employees_id=employee_id, state__in=[Event.STATES[0][0], Event.STATES[1][0]],
                                    day__gte='2023-03-01', day__lte=now_format)
    return events
