# -*- coding: utf-8 -*-
# Hand written @author mehdi

from __future__ import unicode_literals

import csv
import os

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import migrations

from invoices import settings
from django.utils.dateparse import parse_date


def process_codes(apps, schema_editor):
    if 'test' in os.sys.argv:
        return
    updated_codes = []
    codes_that_are_too_old = []
    unknowns = []
    created_codes = []
    path = '2019_may_cns_codes.csv'
    start_date = parse_date("2019-05-01")
    end_date = None
    os.chdir(settings.IMPORTER_CSV_FOLDER)  # changes the directory
    with open(path) as csv_file:
        reader = csv.reader(csv_file, delimiter=';')
        for row in reader:
            if "Section" not in row[0]:
                code = row[1]
                try:
                    care_code = apps.get_model("invoices", "CareCode")
                    care_code_to_updt = care_code.objects.get(code=code)
                    care_code_to_updt.name = row[0][0:49]
                    care_code_to_updt.description = row[0]
                    care_code_to_updt.save()
                except ObjectDoesNotExist:
                    c = care_code(code=code, name=row[0][0:49], description=row[0])
                    c.save()
                validity_date = apps.get_model("invoices", "ValidityDate")
                vs = validity_date.objects.filter(care_code__id=care_code_to_updt.id)
                for v in vs:
                    if v.end_date is None and v.start_date == start_date:
                        v.gross_amount = row[3].replace(',', '.')
                        v.end_date = end_date
                        v.save()
                    elif v.end_date == parse_date("2019-04-30") and v.start_date == parse_date("2019-01-01"):
                        codes_that_are_too_old.append('%s from %s to %s' % (care_code_to_updt.code, v.start_date,
                                                                            v.end_date))
                    elif v.end_date is None and v.start_date == parse_date("2019-01-01"):
                        v.end_date = parse_date("2019-04-30")
                        v.full_clean()
                        v.save()
                        updated_codes.append('%s from %s to %s' % (care_code_to_updt.code, v.start_date, v.end_date))
                    elif v.end_date is not None \
                            and v.end_date < parse_date("2019-04-30") \
                            and v.start_date < start_date:
                        codes_that_are_too_old.append('%s from %s to %s' % (care_code_to_updt.code, v.start_date,
                                                                            v.end_date))
                    else:
                        unknowns.append('%s from %s to %s' % (care_code_to_updt.code, v.start_date, v.end_date))
                current_validity = validity_date.objects.filter(care_code__id=care_code_to_updt.id,
                                                                start_date=parse_date("2019-5-1"),
                                                                end_date=None)
                if current_validity.values().count() != 0:
                    for v in current_validity:
                        v.gross_amount = row[3].replace(',', '.')
                        v.end_date = None
                        v.full_clean()
                        v.save()
                else:
                    v = validity_date(start_date=start_date, gross_amount=row[3].replace(',', '.'),
                                      care_code=care_code_to_updt)
                    v.full_clean()
                    v.save()
                    created_codes.append('%s from %s to %s' % (care_code_to_updt.code, v.start_date, v.end_date))

    print("*** Created codes %s", created_codes)
    print("*** Updated codes %s", updated_codes)
    print("*** Codes Too Old to update %s", codes_that_are_too_old)
    print("*** Unknown Situation Or Nothing to do %s" % unknowns)


class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0064_jan2019_import_cns_prices'),
    ]

    operations = [
        migrations.RunPython(process_codes),
    ]
