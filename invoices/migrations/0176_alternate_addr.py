# Generated by Django 4.1.9 on 2023-07-05 15:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0175_alternate_addr'),
    ]

    operations = [
        migrations.AddField(
            model_name='alternateaddress',
            name='end_time',
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='alternateaddress',
            name='start_time',
            field=models.TimeField(blank=True, null=True),
        ),
    ]