# Generated by Django 4.2.8 on 2023-12-21 16:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0003_contractor_ftr_informal_caregiver'),
    ]

    operations = [
        migrations.AddField(
            model_name='informalcaregiverunavailability',
            name='unavailability_organism_identifier',
            field=models.CharField(blank=True, help_text='Correspond à la référence donnée à la déclaration par l’organisme gestionnaire. Celui-ci sera renseigné dans le fichier retour. Ce champ doit obligatoirement être renseigné lors d’une déclaration de correction.', max_length=50, null=True, verbose_name='Unavailable organism identifier'),
        ),
    ]