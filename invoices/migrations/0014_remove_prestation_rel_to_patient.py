# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-11-21 11:40
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0013_change_rel_invoiceitem_to_prestation'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='prestation',
            name='patient',
        ),
    ]
