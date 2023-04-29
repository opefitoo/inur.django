import csv
from datetime import date

from django.db import transaction

from invoices.models import CareCode, ValidityDate


def update_prices_for_jan_2023(self, request, queryset):


    # Replace 'your_csv_file.csv' with the actual path to your CSV file
    csv_file_path = 'initialdata/2023_JAN_cns_codes.csv'

    # Replace 'your_start_date' with the actual date you want to use
    your_start_date = date(2023, 1, 1)
    your_end_date = date(2023, 1, 31)

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
                            'end_date': your_end_date,
                            'gross_amount': new_gross_amount,
                        }
                    )
                    if not created:
                        validity_date.start_date = your_start_date
                        validity_date.end_date = your_end_date
                        validity_date.gross_amount = new_gross_amount
                        validity_date.save()

                    print(f"Updated CareCode {care_code_str} with gross amount {new_gross_amount}")

def update_prices_for_feb_2023(self, request, queryset):


    # Replace 'your_csv_file.csv' with the actual path to your CSV file
    csv_file_path = 'initialdata/2023_FEB_cns_codes.csv'

    # Replace 'your_start_date' with the actual date you want to use
    your_start_date = date(2023, 2, 1)
    your_end_date = date(2023, 3, 31)


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
                            'end_date': your_end_date,
                            'gross_amount': new_gross_amount,
                        }
                    )
                    if not created:
                        validity_date.start_date = your_start_date
                        validity_date.gross_amount = new_gross_amount
                        validity_date.end_date = your_end_date
                        validity_date.save()

                    print(f"Updated CareCode {care_code_str} with gross amount {new_gross_amount}")


def update_prices_for_april_2023(self, request, queryset):


    # Replace 'your_csv_file.csv' with the actual path to your CSV file
    csv_file_path = 'initialdata/2023_APRIL_cns_codes.csv'
    # Replace 'your_start_date' with the actual date you want to use
    your_start_date = date(2023, 4, 1)


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



def update_prices_for_april_2022(self, request, queryset):


    # Replace 'your_csv_file.csv' with the actual path to your CSV file
    csv_file_path = 'initialdata/2022_april_cns_codes.csv'
    # Replace 'your_start_date' with the actual date you want to use
    your_start_date = date(2022, 4, 1)
    your_end_date = date(2022, 12, 31)

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
                            'end_date': your_end_date,
                            'gross_amount': new_gross_amount,
                        }
                    )
                    if not created:
                        validity_date.start_date = your_start_date
                        validity_date.end_date = your_end_date
                        validity_date.gross_amount = new_gross_amount
                        validity_date.save()

                    print(f"Updated CareCode {care_code_str} with gross amount {new_gross_amount}")
def cleanup_2023(self, request, queryset):
    # Replace 'your_csv_file.csv' with the actual path to your CSV file
    csv_file_path = 'initialdata/2023_FEB_cns_codes.csv'

    # Replace 'your_start_date' with the actual date you want to use
    your_start_date = date(2023, 4, 1)

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
                    # remove all validity dates of 2023
                    deleted = ValidityDate.objects.filter(care_code=care_code, start_date__year=2023).delete()
                    print(f"Deleted {deleted[0]} validity dates for {care_code_str}")


