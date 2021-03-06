# Generated by Django 3.1.5 on 2021-01-20 10:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0087_2021_import_cns_prices'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='at_office',
            field=models.BooleanField(default=False, help_text='Check the box if the event will occur at the office premises', verbose_name='At office premises'),
        ),
        migrations.AddField(
            model_name='event',
            name='event_address',
            field=models.TextField(blank=True, help_text='Enter the address where the event will occur', null=True, verbose_name='Event address'),
        ),
        migrations.AlterField(
            model_name='publicholidaycalendar',
            name='calendar_year',
            field=models.PositiveIntegerField(default=2021),
        ),
        migrations.AlterField(
            model_name='simplifiedtimesheet',
            name='time_sheet_month',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=1),
        ),
        migrations.AlterField(
            model_name='simplifiedtimesheet',
            name='time_sheet_year',
            field=models.PositiveIntegerField(default=2021),
        ),
    ]
