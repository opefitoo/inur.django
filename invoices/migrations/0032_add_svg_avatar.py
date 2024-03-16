# Generated by Django 4.2.11 on 2024-03-10 12:23

from django.db import migrations, models
import invoices.actions.helpers
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0031_agreement_fusion'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='minified_avatar_svg',
            field=models.TextField(blank=True, null=True, verbose_name='Minified Avatar SVG'),
        ),
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
    ]