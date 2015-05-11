# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import opefitoonursev2.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CareCode',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code', models.CharField(max_length=30)),
                ('name', models.CharField(max_length=50)),
                ('description', models.TextField(max_length=100)),
                ('gross_amount', models.DecimalField(verbose_name=b'montant brut', max_digits=5, decimal_places=2)),
            ],
        ),
        migrations.CreateModel(
            name='InvoiceItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('invoice_number', models.CharField(default=opefitoonursev2.models.get_default_invoice_number, max_length=50)),
                ('accident_id', models.CharField(help_text="Numero d'accident est facultatif", max_length=30, null=True, blank=True)),
                ('accident_date', models.DateField(help_text="Date d'accident est facultatif", null=True, blank=True)),
                ('invoice_date', models.DateField(verbose_name=b'Invoice date')),
                ('invoice_sent', models.BooleanField()),
                ('invoice_paid', models.BooleanField()),
                ('medical_prescription_date', models.DateField(null=True, verbose_name=b'Date ordonnance', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Patient',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('code_sn', models.CharField(max_length=30)),
                ('first_name', models.CharField(max_length=30)),
                ('name', models.CharField(max_length=30)),
                ('address', models.TextField(max_length=30)),
                ('zipcode', models.CharField(max_length=10)),
                ('city', models.CharField(max_length=30)),
                ('phone_number', models.CharField(max_length=30)),
                ('participation_statutaire', models.BooleanField()),
                ('private_patient', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Prestation',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(verbose_name=b'date')),
                ('carecode', models.ForeignKey(to='opefitoonursev2.CareCode')),
                ('patient', models.ForeignKey(to='opefitoonursev2.Patient')),
            ],
        ),
        migrations.CreateModel(
            name='PrivateInvoiceItem',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('invoice_number', models.CharField(default=opefitoonursev2.models.get_default_invoice_number, max_length=50)),
                ('accident_id', models.CharField(help_text="Numero d'accident est facultatif", max_length=30, null=True, blank=True)),
                ('accident_date', models.DateField(help_text="Date d'accident est facultatif", null=True, blank=True)),
                ('invoice_date', models.DateField(verbose_name=b'Date facture')),
                ('invoice_send_date', models.DateField(null=True, verbose_name=b'Date envoi facture', blank=True)),
                ('medical_prescription_date', models.DateField(null=True, verbose_name=b'Date ordonnance', blank=True)),
                ('invoice_sent', models.BooleanField()),
                ('invoice_paid', models.BooleanField()),
                ('prestations', models.ManyToManyField(related_name='private_invoice_prestations', editable=False, to='opefitoonursev2.Prestation', blank=True)),
                ('private_patient', models.ForeignKey(related_name='private_invoice_patient', to='opefitoonursev2.Patient', help_text=b'choisir parmi ces patients pour le mois precedent')),
            ],
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='patient',
            field=models.ForeignKey(related_name='patient', to='opefitoonursev2.Patient', help_text=b'choisir parmi ces patients pour le mois precedent'),
        ),
        migrations.AddField(
            model_name='invoiceitem',
            name='prestations',
            field=models.ManyToManyField(related_name='prestations', editable=False, to='opefitoonursev2.Prestation', blank=True),
        ),
    ]
