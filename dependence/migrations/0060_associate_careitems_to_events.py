# Generated by Django 4.1.7 on 2023-03-22 21:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0059_associate_careitems_to_careplan'),
    ]

    operations = [
        migrations.AddField(
            model_name='careplandetail',
            name='name',
            field=models.CharField(default='changer nom', max_length=50, verbose_name='Nom'),
            preserve_default=False,
        ),
    ]
