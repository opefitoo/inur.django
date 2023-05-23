# Generated by Django 4.1.9 on 2023-05-16 09:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0081_invoice_dtl_moved_as_item'),
    ]

    operations = [
        migrations.AddField(
            model_name='longtermcareinvoiceitem',
            name='long_care_item_link',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='from_item_to_long_term_care_item', to='dependence.longtermcareitem'),
        ),
    ]