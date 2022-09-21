# Generated by Django 4.0.6 on 2022-08-07 12:00

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import invoices.db.fields
import invoices.middleware


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('invoices', '0129_aai_and_mode'),
        ('dependence', '0023_enlarge_general_remarks_cleanups'),
    ]

    operations = [
        migrations.AlterField(
            model_name='monthlyparameters',
            name='params_month',
            field=models.IntegerField(choices=[(1, 'Janvier'), (2, 'Février'), (3, 'Mars'), (4, 'Avril'), (5, 'Mai'), (6, 'Juin'), (7, 'Juillet'), (8, 'Août'), (9, 'Septembre'), (10, 'Octobre'), (11, 'Novembre'), (12, 'Décembre')], default=8),
        ),
        migrations.CreateModel(
            name='AAITransmission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transmission_number', models.PositiveSmallIntegerField(verbose_name='Numéro')),
                ('created_on', models.DateTimeField(auto_now_add=True, verbose_name='Date création')),
                ('updated_on', models.DateTimeField(auto_now=True, verbose_name='Dernière mise à jour')),
                ('patient', models.ForeignKey(help_text="Ne recheche que les patients pris en charge par l'assurance dépendance, vérifiez que la checkbox est validé si vous ne trouvez pas votre patient", limit_choices_to={'is_under_dependence_insurance': True}, on_delete=django.db.models.deletion.CASCADE, related_name='aai_to_patient', to='invoices.patient')),
                ('user', invoices.db.fields.CurrentUserField(default=invoices.middleware.get_current_authenticated_user, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Transmission AAI',
                'verbose_name_plural': 'Transmissions AAI',
                'ordering': ['patient__id'],
            },
        ),
        migrations.CreateModel(
            name='AAITransDetail',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('objectives', models.TextField(help_text='Prise en charge, lien avec AEV', max_length=100, verbose_name='Objectifs')),
                ('means', models.TextField(blank=True, default=None, max_length=100, null=True, verbose_name='Moyens/Actions')),
                ('date_time_means_set', models.DateTimeField(blank=True, default=None, null=True, verbose_name='Date/h')),
                ('results', models.TextField(blank=True, default=None, max_length=100, null=True, verbose_name='Résultats')),
                ('date_time_results_set', models.DateTimeField(blank=True, default=None, null=True, verbose_name='Date/h')),
                ('detail_to_aai_master', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='from_aai_detail_to_master', to='dependence.aaitransmission', verbose_name='Détails')),
                ('means_paraph', models.ForeignKey(blank=True, default=None, limit_choices_to=models.Q(('abbreviation__in', ['XXX']), _negated=True), null=True, on_delete=django.db.models.deletion.PROTECT, related_name='employee_of_means', to='invoices.employee', verbose_name='Paraphe')),
                ('results_paraph', models.ForeignKey(blank=True, default=None, limit_choices_to=models.Q(('abbreviation__in', ['XXX']), _negated=True), null=True, on_delete=django.db.models.deletion.PROTECT, related_name='employee_of_results', to='invoices.employee', verbose_name='Paraphe')),
            ],
            options={
                'verbose_name': 'Détail',
                'verbose_name_plural': 'Détails',
                'ordering': ['id'],
            },
        ),
    ]