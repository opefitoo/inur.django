# Generated by Django 4.1.7 on 2023-03-07 12:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0151_some_cleanup_and_tech_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoicingdetails',
            name='aa',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='invoicingdetails',
            name='af',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
        migrations.AddField(
            model_name='invoicingdetails',
            name='rc',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]