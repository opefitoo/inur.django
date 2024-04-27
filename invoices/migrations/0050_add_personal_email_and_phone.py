# Generated by Django 4.2.11 on 2024-04-26 13:23

from django.db import migrations, models
import invoices.actions.helpers
import invoices.models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0049_save_payslips_intodatabase'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='additional_phone_number',
            field=phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, region=None),
        ),
        migrations.AddField(
            model_name='employee',
            name='personal_email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
    ]