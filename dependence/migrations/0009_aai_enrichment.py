# Generated by Django 4.2.10 on 2024-03-04 10:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0008_generic_event_links'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='aaitransdetail',
            name='date_time_results_set',
        ),
        migrations.RemoveField(
            model_name='aaitransdetail',
            name='results_paraph',
        ),
        migrations.AddField(
            model_name='aaitransdetail',
            name='session_duration',
            field=models.DurationField(blank=True, default=None, null=True, verbose_name='Durée'),
        ),
        migrations.AddField(
            model_name='aaitransmission',
            name='aai_month_month',
            field=models.IntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=3),
        ),
        migrations.AddField(
            model_name='aaitransmission',
            name='aai_year',
            field=models.PositiveIntegerField(default=2024),
        ),
        migrations.AlterField(
            model_name='monthlyparameters',
            name='params_month',
            field=models.IntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=3),
        ),
    ]
