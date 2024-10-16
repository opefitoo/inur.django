# Generated by Django 4.2.15 on 2024-08-30 14:56

from django.db import migrations, models
import invoices.actions.helpers
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0062_employee_training_files'),
    ]

    operations = [
        migrations.AddField(
            model_name='subcontractor',
            name='notify_subcontractor',
            field=models.BooleanField(default=False, verbose_name='Notifier le sous-traitant'),
        ),
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
        migrations.AlterField(
            model_name='event',
            name='event_type_enum',
            field=models.CharField(choices=[('BIRTHDAY', 'Birthday'), ('CARE', 'Soin'), ('ASS_DEP', 'Soin Assurance dépendance'), ('GENERIC', 'Général pour Patient (non soin)'), ('GNRC_EMPL', 'Général pour Employé'), ('EMPL_TRNG', 'Formation'), ('SUB_CARE', 'Soin(s) en sous-traitance')], default='CARE', max_length=10, verbose_name='Type'),
        ),
    ]
