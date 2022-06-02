# Generated by Django 4.0.4 on 2022-05-20 11:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0116_add_end_plan_date'),
        ('dependence', '0015_add_pulse'),
    ]

    operations = [
        migrations.AddField(
            model_name='careplanmaster',
            name='plan_end_date',
            field=models.DateField(blank=True, default=None, help_text="Date de la fin d'application du plan des soins", null=True, verbose_name="Jusqu'à:"),
        ),
        migrations.AlterField(
            model_name='monthlyparameters',
            name='params_month',
            field=models.IntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=5),
        ),
        migrations.AlterField(
            model_name='monthlyparameters',
            name='params_year',
            field=models.PositiveIntegerField(default=2022),
        ),
        migrations.AlterField(
            model_name='monthlyparameters',
            name='patient',
            field=models.ForeignKey(limit_choices_to={'is_under_dependence_insurance': True}, on_delete=django.db.models.deletion.PROTECT, related_name='health_params_to_patient', to='invoices.patient'),
        ),
        migrations.AlterField(
            model_name='patientanamnesis',
            name='patient',
            field=models.ForeignKey(limit_choices_to={'is_under_dependence_insurance': True}, on_delete=django.db.models.deletion.PROTECT, related_name='dep_anamnesis_to_patient', to='invoices.patient'),
        ),
    ]