# Generated by Django 4.2.11 on 2024-04-25 19:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0016_enrich_aai'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aaitransdetail',
            name='means',
            field=models.TextField(blank=True, default=None, max_length=500, null=True, verbose_name='Moyens/Actions'),
        ),
    ]
