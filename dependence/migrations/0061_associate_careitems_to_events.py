# Generated by Django 4.1.7 on 2023-03-22 22:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0060_associate_careitems_to_events'),
    ]

    operations = [
        migrations.AddField(
            model_name='careoccurrence',
            name='value',
            field=models.CharField(default='?', max_length=5, verbose_name='Valeur'),
        ),
    ]