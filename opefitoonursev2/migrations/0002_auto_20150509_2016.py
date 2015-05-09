# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('opefitoonursev2', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoiceitem',
            name='prestations',
            field=models.ManyToManyField(related_name='prestations', editable=False, to='opefitoonursev2.Prestation', blank=True),
        ),
    ]
