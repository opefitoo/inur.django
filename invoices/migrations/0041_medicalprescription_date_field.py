# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-12-08 15:44
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0040_medicalprescription_use_gdrive_fs'),
    ]

    operations = [
        migrations.AlterField(
            model_name='medicalprescription',
            name='date',
            field=models.DateField(blank=True, null=True, verbose_name=b'Date ordonnance'),
        ),
    ]
