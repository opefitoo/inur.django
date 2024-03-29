# Generated by Django 4.2.11 on 2024-03-14 15:17

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('dependence', '0012_aai_changes'),
    ]

    operations = [
        migrations.AddField(
            model_name='aaiobjective',
            name='evaluation_date',
            field=models.DateField(default=django.utils.timezone.now, verbose_name="Date d'évaluation"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='aaiobjective',
            name='objective_reaching_date',
            field=models.DateField(default=django.utils.timezone.now, verbose_name="Estimation date d'atteinte de l'objectif"),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='aaiobjective',
            name='status',
            field=models.CharField(choices=[('pending', 'En attente'), ('in_progress', 'En cours'), ('completed', 'Complété'), ('archived', 'Archivé')], default='pending', max_length=15, verbose_name='statut'),
        ),
        migrations.AlterField(
            model_name='aaiobjective',
            name='description',
            field=models.TextField(max_length=1000, verbose_name='Description détaillée'),
        ),
        migrations.CreateModel(
            name='AAIObjectiveFiles',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('file', models.FileField(upload_to='aai_objective_files', verbose_name='Fichier')),
                ('description', models.TextField(blank=True, null=True, verbose_name='Description')),
                ('objective', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='files', to='dependence.aaiobjective')),
            ],
            options={
                'verbose_name': 'Fichier lié à un objectif AAI',
                'verbose_name_plural': 'Fichiers liés à un objectif AAI',
            },
        ),
    ]
