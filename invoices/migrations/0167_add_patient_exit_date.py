# Generated by Django 4.1.8 on 2023-04-29 17:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0166_manage_invoxia_key'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='validitydate',
            options={'ordering': ['-start_date']},
        ),
        migrations.AddField(
            model_name='car',
            name='charge_level',
            field=models.PositiveIntegerField(blank=True, default=0, null=True),
        ),
        migrations.AddField(
            model_name='patient',
            name='date_of_exit',
            field=models.DateField(blank=True, default=None, null=True, verbose_name='Date de sortie'),
        ),
    ]
