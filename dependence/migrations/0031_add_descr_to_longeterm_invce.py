# Generated by Django 4.2.16 on 2024-10-09 11:34

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0030_add_general_remq_hygiene'),
    ]

    operations = [
        migrations.AddField(
            model_name='longtermcaremonthlystatement',
            name='description',
            field=models.TextField(blank=True, null=True, verbose_name='Description'),
        ),
        migrations.AlterField(
            model_name='aaitransmission',
            name='aai_month',
            field=models.IntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=10),
        ),
        migrations.AlterField(
            model_name='longtermcareinvoicefile',
            name='link_to_monthly_statement',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='monthly_statement', to='dependence.longtermcaremonthlystatement'),
        ),
        migrations.AlterField(
            model_name='longtermcaremonthlystatementsending',
            name='link_to_monthly_statement',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='monthly_statement_xml_file', to='dependence.longtermcaremonthlystatement'),
        ),
        migrations.AlterField(
            model_name='monthlyparameters',
            name='params_month',
            field=models.IntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=10),
        ),
    ]