# Generated by Django 4.0.6 on 2022-07-05 11:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0021_enrich_careplan_1'),
    ]

    operations = [
        migrations.AlterField(
            model_name='monthlyparameters',
            name='params_month',
            field=models.IntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=7),
        ),
    ]
