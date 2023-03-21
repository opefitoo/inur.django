# Generated by Django 4.1.7 on 2023-03-21 16:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0157_can_associate_more_than_one_medical_prescription'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoiceitemprescriptionslist',
            name='medical_prescription',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='med_prescription_multi_invoice_items', to='invoices.medicalprescription'),
        ),
    ]
