# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-12-13 21:36
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0044_medical_prescr_change_storage'),
    ]

    operations = [
        migrations.CreateModel(
            name='Hospitalization',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_date', models.DateField(verbose_name="D\xe9but d'hospitlisation")),
                ('end_date', models.DateField(verbose_name='Date de fin')),
                ('description', models.TextField(blank=True, default=None, max_length=50, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='patient',
            name='date_of_death',
            field=models.DateField(blank=True, default=None, null=True, verbose_name='Date de d\xe9c\xe8s'),
        ),
        migrations.AddField(
            model_name='hospitalization',
            name='hospitalizations_periods',
            field=models.ForeignKey(help_text=b'Please enter hospitalization dates of the patient', on_delete=django.db.models.deletion.CASCADE, related_name='patient_hospitalization', to='invoices.Patient'),
        ),
    ]
