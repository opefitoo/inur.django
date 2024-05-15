# Generated by Django 4.2.11 on 2024-05-15 11:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import invoices.actions.helpers
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('invoices', '0053_mobile_app_visits'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='employeevisit',
            name='employee',
        ),
        migrations.AddField(
            model_name='employeevisit',
            name='user',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL, verbose_name='Utilisateur'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
    ]
