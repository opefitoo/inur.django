# Generated by Django 4.2.15 on 2024-08-20 11:22

from django.db import migrations, models
import django.db.models.deletion
import invoices.actions.helpers
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0060_add_insurance_companies'),
    ]

    operations = [
        migrations.CreateModel(
            name='Training',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Nom de la formation')),
                ('description', models.TextField(max_length=200, verbose_name='Description de la formation')),
                ('remote', models.BooleanField(default=False, verbose_name='Formation à distance')),
                ('training_location', models.CharField(blank=True, max_length=100, null=True, verbose_name='Lieu de la formation')),
            ],
        ),
        migrations.AlterModelOptions(
            name='hospitalization',
            options={'ordering': ['-id'], 'verbose_name': 'Hospitalisation ou absence', 'verbose_name_plural': 'Hospitalisations ou absences'},
        ),
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
        migrations.AlterField(
            model_name='hospitalization',
            name='start_date',
            field=models.DateField(verbose_name='Date début'),
        ),
        migrations.CreateModel(
            name='TrainingDates',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('training_start_date_time', models.DateTimeField(verbose_name='Date de début de la formation')),
                ('training_end_date_time', models.DateTimeField(verbose_name='Date de fin de la formation')),
                ('training', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='invoices.training')),
            ],
        ),
        migrations.CreateModel(
            name='EmployeeTraining',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('training_certificate', models.FileField(blank=True, null=True, upload_to='training_certificates/')),
                ('training_completed_date', models.DateField(blank=True, null=True, verbose_name='Date de fin de la formation')),
                ('training_success', models.BooleanField(default=False, verbose_name='Formation réussie')),
                ('training_paid_by_company', models.BooleanField(default=False, verbose_name="Formation payée par l'entreprise")),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='invoices.employee')),
                ('training_link', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='invoices.training')),
            ],
        ),
    ]
