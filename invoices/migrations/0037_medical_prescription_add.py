# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-12-05 17:31
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0036_prestation_employee_allow_blank'),
    ]

    operations = [
        migrations.CreateModel(
            name='MedicalPrescription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('file', models.FileField(upload_to=b'')),
                ('prescriptor', models.ForeignKey(help_text=b'Please chose the Physician who is giving the medical prescription', on_delete=django.db.models.deletion.CASCADE, related_name='medical_prescription', to='invoices.Physician')),
            ],
        ),
    ]
