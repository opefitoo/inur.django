# Generated by Django 4.1.3 on 2022-11-29 16:21

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0133_reportpicture_description'),
    ]

    operations = [
        migrations.CreateModel(
            name='YaleAuthToken',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.JSONField()),
                ('created_by', models.CharField(default='ui', max_length=30)),
                ('created_on', models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                'verbose_name': 'Door Event',
                'verbose_name_plural': 'Door Events',
                'ordering': ['-id'],
            },
        ),
        migrations.AlterField(
            model_name='event',
            name='event_type_enum',
            field=models.CharField(choices=[('BIRTHDAY', 'Birthday'), ('CARE', 'Soin'), ('ASS_DEP', 'Soin Assurance dépendance'), ('GENERIC', 'Général pour Patient (non soin)'), ('GNRC_EMPL', 'Général pour Employé')], default='CARE', max_length=10, verbose_name='Type'),
        ),
        migrations.AlterField(
            model_name='reportpicture',
            name='description',
            field=models.TextField(default='', help_text='Please, give a description of the uploaded image.', max_length=250, verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='reportpicture',
            name='event',
            field=models.ForeignKey(help_text='Here, you can upload pictures if needed', on_delete=django.db.models.deletion.CASCADE, related_name='report_pictures', to='invoices.event'),
        ),
        migrations.AlterField(
            model_name='simplifiedtimesheet',
            name='time_sheet_month',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=11),
        ),
        migrations.CreateModel(
            name='DoorEvent',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('activity_start_time', models.DateTimeField()),
                ('activity_end_time', models.DateTimeField()),
                ('action', models.CharField(default='action', max_length=30)),
                ('activity_type', models.CharField(max_length=40)),
                ('created_by', models.CharField(default='ui', max_length=30)),
                ('created_on', models.DateTimeField(default=django.utils.timezone.now)),
                ('employee', models.ForeignKey(blank=True, help_text='Please select an employee', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='door_event_link_to_employee', to='invoices.employee')),
            ],
            options={
                'verbose_name': 'Door Event',
                'verbose_name_plural': 'Door Events',
                'ordering': ['-id'],
            },
        ),
        migrations.AddConstraint(
            model_name='doorevent',
            constraint=models.UniqueConstraint(fields=('employee', 'activity_start_time', 'activity_end_time', 'activity_type'), name='unique door event'),
        ),
    ]
