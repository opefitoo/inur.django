# Generated by Django 4.1.11 on 2023-09-25 11:26

from django.db import migrations, models
import invoices.actions.helpers
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0185_bedsore_risk_ftr'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
    ]