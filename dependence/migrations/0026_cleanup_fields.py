# Generated by Django 4.2.15 on 2024-08-07 10:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0025_enlarge_dep_rsn'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='patientanamnesis',
            name='plan_of_share',
        ),
        migrations.AlterField(
            model_name='patientanamnesis',
            name='reason_for_dependence',
            field=models.TextField(blank=True, max_length=150, null=True, verbose_name='Motif de prise en charge'),
        ),
    ]
