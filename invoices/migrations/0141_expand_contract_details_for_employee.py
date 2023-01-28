# Generated by Django 4.1.5 on 2023-01-25 16:02

from django.db import migrations, models
import invoices.employee


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0140_create_patient_admin_files'),
    ]

    operations = [
        migrations.AddField(
            model_name='employeecontractdetail',
            name='contract_date',
            field=models.DateField(blank=True, null=True, verbose_name='Date contrat'),
        ),
        migrations.AddField(
            model_name='employeecontractdetail',
            name='contract_signed_date',
            field=models.DateField(blank=True, null=True, verbose_name='Date signature contrat'),
        ),
        migrations.AddField(
            model_name='employeecontractdetail',
            name='employee_contract_file',
            field=models.FileField(blank=True, help_text='You can attach the scan of the contract', null=True, upload_to=invoices.employee.contract_storage_location),
        ),
        migrations.AddField(
            model_name='employeecontractdetail',
            name='employee_special_conditions_text',
            field=models.TextField(blank=True, max_length=200, null=True, verbose_name='Texte conditions spéciales'),
        ),
        migrations.AddField(
            model_name='employeecontractdetail',
            name='employee_trial_period_text',
            field=models.TextField(blank=True, max_length=200, null=True, verbose_name="Texte période d'essai"),
        ),
        migrations.AddField(
            model_name='employeecontractdetail',
            name='salary_index',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True, verbose_name='Index'),
        ),
    ]