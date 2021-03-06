# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-12-29 21:49
from __future__ import unicode_literals

from django.db import migrations, models
import invoices.models
import invoices.storages


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0059_invoiceitem_is_valid_and_comment'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoiceitembatch',
            name='file',
            field=models.FileField(blank=True, storage=invoices.storages.CustomizedGoogleDriveStorage(), upload_to=invoices.models.invoiceitembatch_filename),
        ),
    ]
