# Generated by Django 4.2.11 on 2024-03-25 13:33

from django.db import migrations, models
import invoices.actions.helpers
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0038_car_booking_model'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='carbooking',
            name='booking_start_date',
        ),
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
    ]