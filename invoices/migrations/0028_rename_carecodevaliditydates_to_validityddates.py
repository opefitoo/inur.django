# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-11-30 13:17
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0027_merge_20171130_1308'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='CareCodeValidityDates',
            new_name='ValidityDate',
        ),
    ]
