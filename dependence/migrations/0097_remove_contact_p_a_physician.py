# Generated by Django 4.1.11 on 2023-09-25 11:28

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0096_remove_contact_p_a_physician'),
    ]

    operations = [
        migrations.AlterField(
            model_name='assignedphysician',
            name='anamnesis',
            field=models.ForeignKey(blank=True, default=None, help_text='Please enter hospitalization dates of the patient', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='dep_patient_anamnesis', to='dependence.patientanamnesis'),
        ),
    ]