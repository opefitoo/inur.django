# Generated by Django 3.1.7 on 2021-02-26 18:55

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0096_merge_20210226_1625'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='patientanamnesis',
            name='dep_insurance',
        ),
        migrations.AddField(
            model_name='patientanamnesis',
            name='preferred_hospital',
            field=models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Établissement hospitalier choisi'),
        ),
        migrations.AddField(
            model_name='patientanamnesis',
            name='preferred_pharmacies',
            field=models.TextField(blank=True, default=None, max_length=500, null=True, verbose_name='Pharmacie(s)'),
        ),
        migrations.CreateModel(
            name='OtherStakeholder',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('contact_name', models.CharField(max_length=50, verbose_name='Nom et prénom')),
                ('contact_pro_spec', models.CharField(blank=True, default=None, max_length=20, null=True, verbose_name='Spécialité')),
                ('contact_private_phone_nbr', models.CharField(max_length=30, verbose_name='Tél. privé')),
                ('contact_business_phone_nbr', models.CharField(blank=True, default=None, max_length=30, null=True, verbose_name='Tél. bureau')),
                ('contact_email', models.EmailField(blank=True, default=None, max_length=30, null=True, verbose_name='Email')),
                ('stakeholder_anamnesis', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='stakeholder_to_anamnesis', to='invoices.patientanamnesis')),
            ],
            options={
                'verbose_name': 'Autre intervenant',
                'verbose_name_plural': 'Autres intervenants',
            },
        ),
        migrations.CreateModel(
            name='DependenceInsurance',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('evaluation_date', models.DateField(default=None, verbose_name='Date évaluation')),
                ('ack_receipt_date', models.DateField(blank=True, default=None, null=True, verbose_name='Accusè de réception')),
                ('decision_date', models.DateField(blank=True, default=None, null=True, verbose_name='Date de la décision')),
                ('rate_granted', models.CharField(blank=True, choices=[('REF', 'Refused'), ('ZRO', '0'), ('ONE', '1'), ('TWO', '2'), ('TRE', '3'), ('FOR', '4'), ('FVE', '5'), ('SIX', '6'), ('SVN', '7'), ('EGT', '8'), ('NIN', '9'), ('TEN', '10'), ('ELV', '11'), ('TWV', '12')], default=None, max_length=3, null=True, verbose_name='Forfait')),
                ('dep_anamnesis', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='dep_ins_to_anamnesis', to='invoices.patientanamnesis')),
            ],
            options={
                'verbose_name': 'Décision Assurance dépendance',
                'verbose_name_plural': 'Décisions Assurance dépendance',
                'ordering': ['-id'],
            },
        ),
    ]