# Generated by Django 4.1.7 on 2023-03-03 00:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0039_new_way_of_sending_changes'),
    ]

    operations = [
        migrations.AddField(
            model_name='changedeclarationfile',
            name='force_xml_generation',
            field=models.BooleanField(default=False, verbose_name='Force XML generation'),
        ),
    ]
