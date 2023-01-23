# Generated by Django 4.1.5 on 2023-01-16 18:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0135_avatar_feature'),
    ]

    operations = [
        migrations.AddField(
            model_name='holidayrequest',
            name='do_not_notify',
            field=models.BooleanField(blank=True, default=False, help_text='Do not send email notifications', null=True, verbose_name='Do not notify'),
        ),
        migrations.AlterField(
            model_name='event',
            name='state',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Waiting for validation'), (2, 'Valid'), (3, 'Done'), (4, 'Ignored'), (5, 'Not Done'), (6, 'Cancelled')], verbose_name='State'),
        ),
        migrations.AlterField(
            model_name='publicholidaycalendar',
            name='calendar_year',
            field=models.PositiveIntegerField(default=2023),
        ),
        migrations.AlterField(
            model_name='simplifiedtimesheet',
            name='time_sheet_month',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=1),
        ),
        migrations.AlterField(
            model_name='simplifiedtimesheet',
            name='time_sheet_year',
            field=models.PositiveIntegerField(default=2023),
        ),
    ]