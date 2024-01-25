from datetime import datetime

from django.db import transaction

from invoices.models import Physician


def open_file_and_sync_physicians_from_tsv(file_name):
    with open(file_name) as file:
        sync_physicians_from_tsv(file)

def sync_physicians_from_tsv(file):
    with transaction.atomic():  # Use a transaction to ensure data integrity
        for line in file:
            print("line: %s" % line)
            provider_code = line[:8]  # First 8 characters are the provider code
            print("provider_code: %s" % provider_code)
            full_name_from_cns = line[8:48].strip()  # The rest is the full name, strip leading/trailing spaces
            address = line[48:88].strip()  # The address is in the next 40 characters
            zipcode = line[88:97].strip()  # The zipcode is in the next 9 characters
            # The city is in the next 31 characters
            city = line[97:128].strip()
            cns_speciality_code = line[128:131].strip()  # The CNS speciality code is in the next 3 characters
            # practice_start_date is extracted from the next 8 characters YYYYMMDD
            practice_start_date_str = line[131:139].strip()
            practice_start_date = datetime.strptime(practice_start_date_str, '%Y%m%d').date()
            # practice_end_date is extracted from the next 8 characters YYYYMMDD
            practice_end_date_str = line[139:147].strip()
            practice_end_date = datetime.strptime(practice_end_date_str, '%Y%m%d').date()
            physician, created = Physician.objects.get_or_create(
                provider_code=provider_code,
                defaults={
                    'full_name_from_cns': full_name_from_cns,
                    'address': address,
                    'zipcode': zipcode,
                    'city': city,
                    'cns_speciality_code': cns_speciality_code,
                    # practice_start_date should be converted to date format before saving as it is a string in the TSV
                    'practice_start_date': practice_start_date,
                    # practice_end_date should be converted to date format before saving as it is a string in the TSV
                    'practice_end_date': practice_end_date,
                }
            )

            if not created:
                # Update the existing physician
                physician.full_name_from_cns = full_name_from_cns
                physician.cns_speciality_code = cns_speciality_code
                physician.practice_start_date = datetime.strptime(practice_start_date_str, '%Y%m%d').date()
                physician.practice_end_date = datetime.strptime(practice_end_date_str, '%Y%m%d').date()
                # zipcode and city are updated only if they are different
                if physician.zipcode != zipcode:
                    physician.zipcode = zipcode
                if physician.city != city:
                    physician.city = city
                physician.save()
