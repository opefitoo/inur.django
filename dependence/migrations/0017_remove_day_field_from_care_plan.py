# Generated by Django 4.0.4 on 2022-05-31 15:36

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0016_add_end_plan_date'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='careplandetail',
            name='params_day_of_week',
        ),
    ]