# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('opefitoonursev2', '0002_auto_20150509_2016'),
    ]

    operations = [
        migrations.AlterField(
            model_name='privateinvoiceitem',
            name='prestations',
            field=models.ManyToManyField(related_name='private_invoice_prestations', editable=False, to='opefitoonursev2.Prestation', blank=True),
        ),
    ]
