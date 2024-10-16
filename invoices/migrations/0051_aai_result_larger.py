# Generated by Django 4.2.11 on 2024-04-29 12:33

from django.db import migrations, models
import invoices.actions.helpers
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0050_add_personal_email_and_phone'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
    ]
