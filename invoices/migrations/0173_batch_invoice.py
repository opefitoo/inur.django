# Generated by Django 4.1.9 on 2023-06-15 08:28

from django.db import migrations, models
import invoices.actions.helpers


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0172_batch_invoice'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='invoiceitembatch',
            name='file',
        ),
        migrations.RemoveField(
            model_name='invoiceitembatch',
            name='medical_prescription_files',
        ),
        migrations.AddField(
            model_name='invoiceitembatch',
            name='generated_invoice_files',
            field=models.FileField(blank=True, null=True, upload_to=invoices.actions.helpers.invoice_itembatch_medical_prescription_filename, verbose_name='Facture CNS PDF'),
        ),
        migrations.AddField(
            model_name='invoiceitembatch',
            name='medical_prescriptions',
            field=models.FileField(blank=True, null=True, upload_to=invoices.actions.helpers.invoice_itembatch_ordo_filename, verbose_name='Ordonnances'),
        ),
        migrations.AlterField(
            model_name='invoiceitembatch',
            name='prefac_file',
            field=models.FileField(blank=True, null=True, upload_to=invoices.actions.helpers.invoice_itembatch_prefac_filename, verbose_name='Fichier Plat facturation'),
        ),
    ]
