# -*- coding: utf-8 -*-
# Hand written @author mehdi

from __future__ import unicode_literals

import csv
import os

from django.core.exceptions import ObjectDoesNotExist
from django.db import migrations

from invoices import settings
from django.utils.dateparse import parse_date


def process_codes(apps, schema_editor):
    if 'test' in os.sys.argv:
        return
    updated_codes = []
    codes_that_are_too_old = []
    unknowns = []
    path = '2019cns_codes.csv'
    start_date = parse_date("2019-01-01")
    end_date = parse_date("2019-04-30")
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
                    validity_date = apps.get_model("invoices", "ValidityDate")
                    vs = validity_date.objects.filter(care_code__id=care_code_to_updt.id)
                    need_new_vdate = False
                    for v in vs:
                        if (v.end_date is None or v.end_date < start_date) \
                                and v.start_date == start_date:
                            v.gross_amount = row[3].replace(',', '.')
                            v.end_date = end_date
                            v.save()
                            updated_codes.append(
                                '%s from %s to %s' % (care_code_to_updt.code, v.end_date, v.start_date))
                        elif v.end_date is not None and v.end_date < start_date and v.start_date < start_date:
                            need_new_vdate = True
                        elif v.end_date == end_date and v.start_date == start_date:
                            v.gross_amount = row[3].replace(',', '.')
                            v.save()
                            need_new_vdate = False
                            break
                        else:
                            unknowns.append('%s from %s to %s' % (care_code_to_updt.code, v.start_date, v.end_date))
                    if need_new_vdate:
                        validity_date = apps.get_model("invoices", "ValidityDate")
                        v_new = validity_date(start_date=start_date, end_date=end_date,
                                              gross_amount=row[3].replace(',', '.'), care_code=care_code_to_updt)
                        v_new.save()
                        codes_that_are_too_old.append('%s from %s to %s' % (care_code_to_updt.code, v_new.start_date,
                                                                            v_new.end_date))

                except ObjectDoesNotExist:
                    c = care_code(code=code, name=row[0][0:49], description=row[0])
                    c.save()
                    validity_date = apps.get_model("invoices", "ValidityDate")
                    v = validity_date(start_date=start_date, end_date=end_date,
                                      gross_amount=row[3].replace(',', '.'), care_code=c)
                    v.save()
    print("*** Updated codes %s", updated_codes)
    print("*** Codes Old and being updated %s", codes_that_are_too_old)
    print("*** Unknown Situation Or Nothing to do %s" % unknowns)


class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0063_enlarge_description_care_code'),
    ]

    operations = [
        migrations.RunPython(process_codes),
    ]
