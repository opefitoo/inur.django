# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-11-28 11:34
from __future__ import unicode_literals

from django.db import migrations
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0022_patient_add_country'),
    ]

    operations = [
        migrations.AlterField(
            model_name='patient',
            name='country',
            field=django_countries.fields.CountryField(blank=True, max_length=2, null=True),
        ),
    ]
