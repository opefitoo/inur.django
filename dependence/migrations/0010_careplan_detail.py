# Generated by Django 3.2.8 on 2021-10-14 13:12

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0009_careplan_detail'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='careplanmaster',
            options={'ordering': ['patient__id'], 'verbose_name': 'Plan de Soins Détaillé', 'verbose_name_plural': 'Plans de Soins Détaillé'},
        ),
        migrations.AddField(
            model_name='careplanmaster',
            name='plan_start_date',
            field=models.DateField(default=datetime.date(2021, 10, 14), help_text="Date du début d'application du plan des soins", verbose_name='À partir de:'),
        ),
    ]