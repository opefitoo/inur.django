# Generated by Django 4.1.8 on 2023-05-08 15:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0075_create_monthly_activity_file_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='longtermmonthlyactivityfile',
            name='monthly_activities',
            field=models.ManyToManyField(blank=True, to='dependence.longtermmonthlyactivity', verbose_name='Activities'),
        ),
    ]
