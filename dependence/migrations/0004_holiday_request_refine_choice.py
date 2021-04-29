# Generated by Django 3.2 on 2021-04-29 09:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0003_move_habits_to_inlines'),
    ]

    operations = [
        migrations.AlterField(
            model_name='socialhabits',
            name='habit_type',
            field=models.CharField(blank=True, choices=[('FML', 'Famille'), ('FRND', 'Amis'), ('IMP', 'Personnes importantes')], default=None, max_length=4, null=True, verbose_name='Type'),
        ),
    ]
