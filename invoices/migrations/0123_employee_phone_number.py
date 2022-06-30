# Generated by Django 4.0.5 on 2022-06-29 16:31

from django.db import migrations, models
import django.db.models.deletion
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0122_employee_admin_files'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='bank_account_number',
            field=models.CharField(blank=True, max_length=50, verbose_name='Numéro de compte IBAN'),
        ),
        migrations.AddField(
            model_name='employee',
            name='phone_number',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, region=None),
        ),
        migrations.AlterField(
            model_name='invoiceitem',
            name='medical_prescription',
            field=models.ForeignKey(blank=True, help_text='Please choose a Medical Prescription', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='invoice_items', to='invoices.medicalprescription'),
        ),
    ]