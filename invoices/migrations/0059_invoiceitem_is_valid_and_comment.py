# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-12-29 11:56
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0058_invoice_batch_on_delete'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoiceitem',
            name='is_valid',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='validation_comment',
            field=models.TextField(blank=True, null=True),
        ),
    ]
