# Generated by Django 4.1.7 on 2023-03-02 14:41

import dependence.dependanceinsurance
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0033_create_longterm_care'),
    ]

    operations = [
        migrations.AddField(
            model_name='longtermcaredeclaration',
            name='manually_generated_xml',
            field=models.FileField(blank=True, null=True, upload_to=dependence.dependanceinsurance.long_term_care_declaration_file_path, verbose_name='Manually generated XML'),
        ),
        migrations.AddField(
            model_name='longtermcaredeclaration',
            name='month_of_count',
            field=models.IntegerField(default=3, verbose_name='Month of count'),
        ),
        migrations.AddField(
            model_name='longtermcaredeclaration',
            name='year_of_count',
            field=models.IntegerField(default=2023, verbose_name='Year of count'),
        ),
        migrations.AlterField(
            model_name='longtermcaredeclaration',
            name='information',
            field=models.TextField(help_text='Ce champ est optionnel et peut contenir du texte libre.', max_length=50, verbose_name='Information'),
        ),
    ]
