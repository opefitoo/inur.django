# Generated by Django 4.1.9 on 2023-05-16 09:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0082_invoice_dtl_moved_as_item'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='longtermcareinvoiceitem',
            name='long_term_care_package',
        ),
    ]