# Generated by Django 4.2.15 on 2024-08-17 14:06

from django.db import migrations, models
import invoices.actions.helpers
import invoices.models
import phonenumber_field.modelfields


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0059_skip_aev_checks'),
    ]

    operations = [
        migrations.CreateModel(
            name='InsuranceCompany',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('description', models.CharField(max_length=255)),
                ('address', models.TextField(max_length=255)),
                ('phone_number', phonenumber_field.modelfields.PhoneNumberField(max_length=128, region=None, verbose_name='Numéro de tél.')),
                ('fax_number', phonenumber_field.modelfields.PhoneNumberField(blank=True, max_length=128, null=True, region=None, verbose_name='Numéro de fax')),
                ('email_address', models.EmailField(blank=True, default=None, max_length=254, null=True)),
                ('website', models.URLField(blank=True, null=True, verbose_name='Site web')),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Date création')),
                ('updated_on', models.DateTimeField(auto_now=True, verbose_name='Dernière mise à jour')),
            ],
        ),
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
        migrations.AlterField(
            model_name='simplifiedtimesheet',
            name='time_sheet_month',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=8),
        ),
        migrations.AddField(
            model_name='patient',
            name='insurance_companies',
            field=models.ManyToManyField(blank=True, to='invoices.insurancecompany'),
        ),
    ]
