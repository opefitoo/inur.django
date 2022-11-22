import re

from django.utils import timezone

from invoices.enums.event import EventTypeEnum
from invoices.events import EventType, Event
from invoices.models import Patient, extract_birth_date, calculate_age


def process_and_generate(num_days: int):
    events_processed = []
    even_type_birthday = EventType.objects.filter(to_be_generated=True, name__icontains='Birthdays').first()
    if not even_type_birthday:
        even_type_birthday = EventType(
            name='Birthdays',
            to_be_generated=True
        )
        even_type_birthday.save()

    this_day = timezone.datetime.today()
    last_day = this_day + timezone.timedelta(days=+num_days)

    patients = list_patients_with_birth_date_in_range_still_alive(this_day, last_day)
    for patient in patients:
        patient_birthday = extract_birth_date(patient.code_sn)
        if patient_birthday.replace(year=last_day.year) <= last_day:
            searches_date = timezone.now().replace(last_day.year, patient_birthday.month, patient_birthday.day)
            events = Event.objects.filter(day=searches_date).filter(event_type__name='Birthdays')
            if not events and patient.date_of_death is None:
                event = Event(
                    day=searches_date,
                    state=1,
                    time_start_event=timezone.now().replace(hour=8, minute=0, second=0, microsecond=0).time(),
                    event_type=even_type_birthday,
                    event_type_enum=EventTypeEnum.BIRTHDAY,
                    notes='%s will turn %d \n generated on %s' % (patient,
                                                                  calculate_age(None, patient.code_sn),
                                                                  timezone.now()),
                    patient=patient
                )
                event.save()
                events_processed.append(event)
            else:
                for e in events:
                    events_processed.append(e)

    return events_processed


def list_patients_with_birth_date_in_range_still_alive(start_date_range, end_date_range):
    my_regexp = re.compile(
        '^[0-9]{4}(' + _build_date_range_in_regexp(start_date_range, end_date_range) + ')')
    return Patient.objects.filter(code_sn__regex=my_regexp.pattern).filter(date_of_death__isnull=True)


def _build_date_range_in_regexp(start_date, end_date):
    dateDelta = (end_date - start_date).days
    STR = ''
    for date in range(dateDelta + 1):
        focusedDate = start_date + timezone.timedelta(date)
        STR += focusedDate.strftime("%m%d") + '|'
    STR = STR[:-1]
    return STR
