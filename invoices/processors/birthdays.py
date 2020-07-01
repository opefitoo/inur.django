import re

from django.utils import timezone

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

    thisday = timezone.datetime.today()
    lastday = thisday + timezone.timedelta(days=+num_days)

    myregexp = re.compile('^[0-9]{4}(' + str(thisday.month).zfill(2) + '|' + str(lastday.month).zfill(2) + ')')

    patients = Patient.objects.filter(code_sn__regex=myregexp.pattern).filter(date_of_death__isnull=True)
    for patient in patients:
        patient_birthday = extract_birth_date(patient.code_sn)
        if patient_birthday.replace(year=lastday.year) <= lastday:
            searches_date = timezone.now().replace(lastday.year, patient_birthday.month, patient_birthday.day)
            events = Event.objects.filter(day=searches_date)
            if not events:
                event = Event(
                    day=searches_date,
                    state=1,
                    event_type=even_type_birthday,
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
