# Generated by Django 4.1.1 on 2022-09-20 11:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0025_add_create_update_dates_on_timesheets'),
    ]

    operations = [
        migrations.AddField(
            model_name='tensionandtemperatureparameters',
            name='vas',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(0, '0 (aucune douleur)'), (1, '1 (simple inconfort)'), (2, '2 (simple inconfort+)'), (3, '3 (douleur légère)'), (4, '4 (douleur légère+)'), (5, '5 (douleur modérée)'), (6, '6 (douleur modérée+)'), (7, '7 (douleur intense)'), (8, '8 (douleur intense+)'), (9, '9 (douleur intolérable)'), (10, '10 (douleur intolérable+)')], default=None, null=True, verbose_name='EVA'),
        ),
        migrations.AlterField(
            model_name='monthlyparameters',
            name='params_month',
            field=models.IntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=9),
        ),
    ]