# Generated by Django 4.2.11 on 2024-04-25 19:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0015_report_picture_chat_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='aaitransdetail',
            name='transmission_picture',
            field=models.ImageField(blank=True, default=None, null=True, upload_to='AAI/transmission_pictures', verbose_name='Photo'),
        ),
        migrations.AlterField(
            model_name='aaitransdetail',
            name='means',
            field=models.TextField(blank=True, default=None, max_length=300, null=True, verbose_name='Moyens/Actions'),
        ),
        migrations.AlterField(
            model_name='aaitransdetail',
            name='results',
            field=models.TextField(blank=True, default=None, max_length=300, null=True, verbose_name='Résultats'),
        ),
    ]