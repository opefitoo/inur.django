# Generated by Django 4.2.15 on 2024-08-19 12:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0028_main_doctor'),
    ]

    operations = [
        migrations.AddField(
            model_name='contactperson',
            name='contact_address',
            field=models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Adresse'),
        ),
        migrations.AlterField(
            model_name='patientanamnesis',
            name='legal_protection_regimes',
            field=models.CharField(blank=True, choices=[('TUT', 'Tutelle'), ('CUR', 'Curatelle'), ('SAV', 'Sauvegarde de justice'), ('OTH', 'Autre'), ('NONE', 'Aucun'), ('ND', 'Non Connu')], default=None, max_length=50, null=True, verbose_name='Régimes de protection légale'),
        ),
    ]
