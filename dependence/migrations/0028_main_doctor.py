# Generated by Django 4.2.15 on 2024-08-18 18:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0027_legal_protection_regimes'),
    ]

    operations = [
        migrations.AddField(
            model_name='assignedphysician',
            name='main_attending_physician',
            field=models.BooleanField(default=False, verbose_name='Traitant principal'),
        ),
    ]