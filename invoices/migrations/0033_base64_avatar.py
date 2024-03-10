# Generated by Django 4.2.11 on 2024-03-10 16:26

from django.db import migrations, models
import invoices.actions.helpers
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0032_add_svg_avatar'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employee',
            name='minified_avatar_svg',
        ),
        migrations.AddField(
            model_name='employee',
            name='minified_avatar_base64',
            field=models.TextField(blank=True, null=True, verbose_name='Minified Avatar Base64 encoded'),
        ),
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
    ]
