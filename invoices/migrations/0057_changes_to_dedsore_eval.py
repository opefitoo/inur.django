# Generated by Django 4.2.11 on 2024-06-18 12:54

from django.db import migrations, models

import invoices.actions.helpers
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0056_migrate_latitudes'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='bedsoreevaluation',
            options={'ordering': ['evaluation_date'], 'verbose_name': 'Evaluation', 'verbose_name_plural': 'Evaluations'},
        ),
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='stage',
            field=models.IntegerField(choices=[(1, 'Stade 1'), (2, 'Stade 2'), (3, 'Stade 3'), (4, 'Stade 4')]),
        ),
    ]
