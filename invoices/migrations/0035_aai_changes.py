# Generated by Django 4.2.11 on 2024-03-14 15:17

from django.db import migrations, models
import invoices.actions.helpers
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0034_aai_changes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
    ]