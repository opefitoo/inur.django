# Generated by Django 4.1.7 on 2023-03-04 20:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0046_spc'),
    ]

    operations = [
        migrations.AlterField(
            model_name='longtermcareitem',
            name='code',
            field=models.CharField(max_length=10, unique=True),
        ),
    ]
