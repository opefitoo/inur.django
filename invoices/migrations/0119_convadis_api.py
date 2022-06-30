# Generated by Django 4.0.5 on 2022-06-22 16:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0118_enrich_careplan_1'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConvadisOAuth2Token',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.JSONField()),
            ],
        ),
        migrations.AddField(
            model_name='car',
            name='convadis_identifier',
            field=models.CharField(blank=True, default=None, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='car',
            name='is_connected_to_convadis',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='expensecard',
            name='pin',
            field=models.CharField(default='1111', max_length=8),
        ),
    ]