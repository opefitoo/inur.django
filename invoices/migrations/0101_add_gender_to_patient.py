# Generated by Django 3.2 on 2021-04-12 12:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0100_payment_ref'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='medicalprescription',
            name='image_file',
        ),
        migrations.AddField(
            model_name='patient',
            name='gender',
            field=models.CharField(blank=True, choices=[('MAL', 'Male'), ('FEM', 'Female'), ('OTH', 'Other')], default=None, max_length=5, null=True, verbose_name='Sex'),
        ),
        migrations.AlterField(
            model_name='simplifiedtimesheet',
            name='time_sheet_month',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=4),
        ),
    ]