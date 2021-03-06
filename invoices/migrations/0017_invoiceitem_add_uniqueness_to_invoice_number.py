# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-11-21 12:50
from __future__ import unicode_literals

from django.db import migrations, models
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0016_upd_relation_names_on_foreign_keys'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoiceitem',
            name='invoice_number',
            field=models.CharField(default=invoices.models.get_default_invoice_number, max_length=50, unique=True),
        ),
    ]
