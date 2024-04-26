# Generated by Django 4.2.11 on 2024-04-26 09:34

from django.db import migrations, models
import invoices.actions.helpers
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0048_save_payslips_intodatabase'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
        migrations.AlterField(
            model_name='employeepayslip',
            name='file',
            field=models.FileField(upload_to='payslip_per_employee/'),
        ),
        migrations.AlterField(
            model_name='employeepayslip',
            name='net_salary',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='employeepayslip',
            name='salary',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
    ]
