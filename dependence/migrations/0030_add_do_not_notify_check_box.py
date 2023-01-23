# Generated by Django 4.1.5 on 2023-01-16 18:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0029_avatar_feature'),
    ]

    operations = [
        migrations.AlterField(
            model_name='monthlyparameters',
            name='params_month',
            field=models.IntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=1),
        ),
        migrations.AlterField(
            model_name='monthlyparameters',
            name='params_year',
            field=models.PositiveIntegerField(default=2023),
        ),
    ]