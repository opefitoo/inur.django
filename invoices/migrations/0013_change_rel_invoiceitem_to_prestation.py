# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-11-21 11:49
from __future__ import unicode_literals

import calendar
import datetime
from django.db import migrations, models
import django.db.models.deletion


def migrate_relation_data(apps, schema_editor):
    InvoiceItemModel = apps.get_model('invoices', 'InvoiceItem')
    for invoice_item in InvoiceItemModel.objects.all():
        for invoice_item_prestation in invoice_item.prestations.all():
            invoice_item_prestation.invoice_item_id = invoice_item.id
            invoice_item_prestation.save()


def create_invoices_for_orphan_prestations(apps, schema_editor):
    groups = {}
    InvoiceItemModel = apps.get_model('invoices', 'InvoiceItem')
    PrestationModel = apps.get_model('invoices', 'Prestation')
    for prestation in PrestationModel.objects.filter(invoice_item=None):
        month = prestation.date.month
        patient_id = prestation.patient_id
        patient_group = {
            'patient': prestation.patient,
            'months': {}
        }
        if patient_id in groups:
            patient_group = groups[patient_id]

        date = datetime.datetime(prestation.date.year, prestation.date.month, calendar.mdays[prestation.date.month])
        month_group = {
            'date': date,
            'prestations': []
        }
        if month in patient_group['months']:
            month_group = patient_group['months'][month]

        month_group['prestations'].append(prestation)

        patient_group['months'][month] = month_group
        groups[patient_id] = patient_group

    for patient_group in groups.values():
        patient = patient_group['patient']
        for month_group in patient_group['months'].values():
            invoice_item = InvoiceItemModel()
            invoice_item.invoice_date = month_group['date']
            invoice_item.invoice_sent = False
            invoice_item.invoice_paid = False

            invoice_item.patient_id = patient.id
            invoice_item.is_private = patient.private_patient
            invoice_item.save()

            for prestation in month_group['prestations']:
                prestation.invoice_item = invoice_item
                prestation.save()


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0012_get_rid_of_private_invoice_item'),
    ]

    operations = [
        migrations.RunSQL('SET CONSTRAINTS ALL IMMEDIATE',
                          reverse_sql=migrations.RunSQL.noop),
        migrations.AddField(
            model_name='prestation',
            name='invoice_item',
            field=models.ForeignKey(default=None, null=True, on_delete=django.db.models.deletion.CASCADE, to='invoices.InvoiceItem'),
            preserve_default=False,
        ),
        migrations.RunPython(migrate_relation_data),
        migrations.RemoveField(
            model_name='invoiceitem',
            name='prestations',
        ),
        migrations.RunPython(create_invoices_for_orphan_prestations),
        migrations.AlterField(
            model_name='prestation',
            name='invoice_item',
            field=models.ForeignKey(null=False, on_delete=django.db.models.deletion.CASCADE, to='invoices.InvoiceItem'),
        ),
        migrations.RunSQL(migrations.RunSQL.noop,
                          reverse_sql='SET CONSTRAINTS ALL IMMEDIATE'),
    ]
