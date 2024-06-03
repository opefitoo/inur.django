# Generated by Django 4.2.11 on 2024-05-15 10:15

from django.db import migrations, models
import django.db.models.deletion
import invoices.actions.helpers
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0052_batch_12_pct'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
        migrations.AlterField(
            model_name='invoiceitembatch',
            name='generated_12_percent_invoice_files',
            field=models.FileField(blank=True, null=True, upload_to=invoices.actions.helpers.invoice_itembatch_12_pct_filename, verbose_name='Facture 12% PDF'),
        ),
        migrations.CreateModel(
            name='EmployeeVisit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('latitude', models.FloatField(verbose_name='Latitude')),
                ('longitude', models.FloatField(verbose_name='Longitude')),
                ('arrival_date_time', models.DateTimeField(verbose_name='Arrivée')),
                ('departure_date_time', models.DateTimeField(blank=True, null=True, verbose_name='Départ')),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='invoices.employee', verbose_name='Employé')),
                ('patient', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='invoices.patient', verbose_name='Patient')),
            ],
            options={
                'verbose_name': "Visite d'employé",
                'verbose_name_plural': "Visites d'employés",
            },
        ),
    ]