# Generated by Django 4.0.5 on 2022-06-27 16:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0119_convadis_api'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='car',
            options={'ordering': ['-name'], 'verbose_name': 'Voiture, Clé ou coffre', 'verbose_name_plural': 'Voitures, Clés ou coffres'},
        ),
        migrations.AlterField(
            model_name='simplifiedtimesheet',
            name='extra_hours_paid_current_month',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=4, verbose_name='Heures supp. payées ou récupérées pour le mois courant'),
        ),
    ]