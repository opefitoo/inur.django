from django.core.management.base import BaseCommand, CommandError
from invoices.events import Event, EventType
from invoices.models import Patient, extract_birth_date
from django.db.models import Q
import re
import datetime

class Command(BaseCommand):
    help = 'Checks for patient birthdays'

    def handle(self, *args, **options):
            eventype = EventType.objects.get(name='Birthdays')

            thisday = datetime.date.today()
            lastday = thisday+ datetime.timedelta(days=+30)

            myregexp=re.compile('^[0-9]{4}('+str(thisday.month).zfill(2)+'|'+str(lastday.month).zfill(2)+')')


            patients = Patient.objects.filter(code_sn__regex=myregexp.pattern)
            for patient in patients:
                patient_birthday=extract_birth_date(patient.code_sn)
                if (patient_birthday.date()>lastday):
                    continue
                active_year = thisday.year    
                if (patient_birthday.month!=thisday.month):
                    active_year = lastday.year
                searches_date=datetime.date(active_year,patient_birthday.month,patient_birthday.day)    
                events = Event.objects.filter(day=searches_date)
                if not events:
                    event= Event(
                        day = searches_date,
                        state = 1,
                        event_type = eventype,
                        notes = 'test',
                        patient = patient 
                        )
                    event.save()

            self.stdout.write(self.style.SUCCESS('Successfully printed all patients having a birthday'))
            return

