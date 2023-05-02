# Generated by Django 4.1.8 on 2023-04-30 18:03

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0168_add_patient_exit_date'),
        ('dependence', '0067_invoicing_aev'),
    ]

    operations = [
        migrations.AlterField(
            model_name='declarationdetail',
            name='patient',
            field=models.ForeignKey(help_text='Only looks for patients covered by long-term care insurance, check that the checkbox is validated if you cannot find your patient', limit_choices_to={'is_under_dependence_insurance': True}, on_delete=django.db.models.deletion.CASCADE, related_name='declaration_dtl_to_patient', to='invoices.patient'),
        ),
    ]