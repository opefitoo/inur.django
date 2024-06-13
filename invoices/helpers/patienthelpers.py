from datetime import datetime

from django.db.models import Count

from invoices.enums.event import EventTypeEnum
from invoices.events import Event
from invoices.models import Patient


def list_patients_who_had_events_at_least_5_times_since_one_year():
    """
    List patients who had events at least 5 times the previous year
    """
    # Get the current year
    current_year = datetime.now().year
    # Get the previous year
    previous_year = current_year - 1
    # Get the date range from now to one year ago
    start_date = datetime(previous_year, 1, 1)
    end_date = datetime(previous_year, 12, 31)
    # Get the events for the previous year
    events = Event.objects.filter(day__range=[start_date, end_date]).exclude(event_type_enum=EventTypeEnum.BIRTHDAY)
    patient_ids = []
    for event in events:
        if event.patient and event.patient.id not in patient_ids:
            patient_ids.append(event.patient.id)
    # Get the patients who had events at least 5 times
    patient_ids = Patient.objects.filter(id__in=patient_ids).annotate(
        num_events=Count('event')).filter(num_events__gte=5)
    return patient_ids
