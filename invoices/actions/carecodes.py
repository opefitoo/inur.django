import csv
from datetime import date

from django.db import transaction

from invoices.models import CareCode, ValidityDate


def update_prices_for_january_2023(self, request, queryset):


    # Replace 'your_csv_file.csv' with the actual path to your CSV file
    csv_file_path = 'initialdata/2023_JAN_cns_codes.csv'

    # Replace 'your_start_date' with the actual date you want to use
    your_start_date = date(2023, 1, 1)

    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile, delimiter=';', quotechar='"')

        with transaction.atomic():
            for row in reader:
                print(row)
                if len(row) < 4:
                    continue
                care_code_str = row[1].strip()
                new_gross_amount = float(row[3].strip())

                care_code = CareCode.objects.filter(code=care_code_str).first()

                if care_code:
                    validity_date, created = ValidityDate.objects.update_or_create(
                        care_code=care_code,
                        end_date=None,
                        defaults={
                            'start_date': your_start_date,
                            'gross_amount': new_gross_amount,
                        }
                    )
                    if not created:
                        validity_date.start_date = your_start_date
                        validity_date.gross_amount = new_gross_amount
                        validity_date.save()

                    print(f"Updated CareCode {care_code_str} with gross amount {new_gross_amount}")

