# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-12-14 13:13
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0044_medical_prescr_change_storage'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='has_gdrive_access',
            field=models.BooleanField(default=False, verbose_name=b"Allow access to Medical Prescriptions' scans"),
        ),
    ]
