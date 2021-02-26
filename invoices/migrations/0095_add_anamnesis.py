# Generated by Django 3.1.7 on 2021-02-26 15:08

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django_countries.fields


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0094_add_invoicing_details'),
    ]

    operations = [
        migrations.AddField(
            model_name='physician',
            name='physician_speciality',
            field=models.CharField(blank=True, default=None, max_length=30, null=True),
        ),
        migrations.AlterField(
            model_name='invoicingdetails',
            name='email_address',
            field=models.EmailField(blank=True, default=None, max_length=254, null=True, validators=[django.core.validators.EmailValidator]),
        ),
        migrations.CreateModel(
            name='PatientAnamnesis',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nationality', django_countries.fields.CountryField(blank=True, max_length=2, null=True, verbose_name='Nationalité')),
                ('spoken_languages', models.CharField(blank=True, default=None, max_length=40, null=True, verbose_name='Langues parlées')),
                ('external_doc_link', models.URLField(blank=True, default=None, null=True, verbose_name='URL doc. externe')),
                ('civil_status', models.CharField(blank=True, choices=[('SINGLE', 'Single'), ('MARRIED', 'Married'), ('WIDOW', 'Widow'), ('PACS', 'Pacs')], default=None, max_length=7, null=True, verbose_name='État civil')),
                ('house_type', models.CharField(blank=True, choices=[('FLAT', 'Flat'), ('HOUSE', 'House')], default=None, max_length=5, null=True, verbose_name="Type d'habitation")),
                ('floor_number', models.PositiveSmallIntegerField(blank=True, default=None, null=True, verbose_name='Étage')),
                ('ppl_circle', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Entourage')),
                ('door_key', models.BooleanField(blank=True, default=None, null=True, verbose_name='Clé')),
                ('entry_door', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name="Porte d'entrée")),
                ('health_care_dossier_location', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Dossier de soins se trouve')),
                ('informal_caregiver', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Aidant informel')),
                ('dep_insurance', models.BooleanField(default=False, verbose_name='Assurance dépendance')),
                ('pathologies', models.TextField(blank=True, default=None, max_length=500, null=True, verbose_name='Pahologies')),
                ('medical_background', models.TextField(blank=True, default=None, max_length=500, null=True, verbose_name='Antécédents')),
                ('allergies', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Allergies')),
                ('electrical_bed', models.BooleanField(blank=True, default=None, null=True, verbose_name='Lit électrique')),
                ('walking_frame', models.BooleanField(blank=True, default=None, null=True, verbose_name='Cadre de marche')),
                ('cane', models.BooleanField(blank=True, default=None, null=True, verbose_name='Canne')),
                ('aqualift', models.BooleanField(blank=True, default=None, null=True, verbose_name='Aqualift')),
                ('remote_alarm', models.CharField(blank=True, choices=[('RK', 'Roude Knap'), ('SDHM', 'Secher Doheem'), ('HLP', 'Help')], default=None, max_length=4, null=True, verbose_name='Alarme')),
                ('other_technical_help', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Autres aides techniques')),
                ('dental_prosthesis', models.CharField(blank=True, choices=[('HI', 'High'), ('LO', 'Low'), ('CMPLT', 'Complete')], default=None, max_length=5, null=True, verbose_name='Prothèses dentaires')),
                ('hearing_aid', models.CharField(blank=True, choices=[('RIT', 'Right'), ('LFT', 'Left'), ('BTH', 'Both')], default=None, max_length=4, null=True, verbose_name='Appareil auditif')),
                ('glasses', models.BooleanField(blank=True, default=None, null=True, verbose_name='Lunettes')),
                ('other_prosthesis', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Autres')),
                ('drugs_managed_by', models.CharField(blank=True, choices=[('AUTNM', 'Autonomous'), ('FML', 'Family'), ('NTWRK', 'Network')], default=None, max_length=5, null=True, verbose_name='Prise en charge')),
                ('drugs_prepared_by', models.CharField(blank=True, default=None, max_length=30, null=True, verbose_name='Prépraration')),
                ('drugs_distribution', models.CharField(blank=True, default=None, max_length=30, null=True, verbose_name='Distribution')),
                ('drugs_ordering', models.CharField(blank=True, default=None, max_length=30, null=True, verbose_name='Commande des médicaments')),
                ('pharmacy_visits', models.CharField(blank=True, default=None, max_length=30, null=True, verbose_name='Passages en pharmacie')),
                ('mobilization', models.CharField(blank=True, choices=[('AUTNM', 'Autonomous'), ('TCNQ', 'With technical help'), ('TRD', 'With third party'), ('BD', 'Bedridden')], default=None, max_length=5, null=True, verbose_name='Mobilisation')),
                ('mobilization_description', models.TextField(blank=True, default=None, max_length=250, null=True, verbose_name='Description')),
                ('hygiene_care_location', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Les soins se déroulent où?')),
                ('shower_days', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Jours de douche')),
                ('hair_wash_days', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Lavage cheveux')),
                ('bed_manager', models.CharField(blank=True, choices=[('AUTNM', 'Autonomous'), ('FML', 'Family'), ('NTWRK', 'Network')], default=None, max_length=5, null=True, verbose_name='Le lit est à faire par')),
                ('bed_sheets_manager', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Changement des draps')),
                ('laundry_manager', models.CharField(blank=True, choices=[('AUTNM', 'Autonomous'), ('FML', 'Family'), ('NTWRK', 'Network')], default=None, max_length=5, null=True, verbose_name='Linge est à faire par')),
                ('laundry_drop_location', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Le linge sale est à déposer où ?')),
                ('new_laundry_location', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Les vêtements/serviettes etc. se trouvent où ?')),
                ('weight', models.PositiveSmallIntegerField(default=None, verbose_name='Poids')),
                ('size', models.PositiveSmallIntegerField(default=None, verbose_name='Taille en cm.')),
                ('nutrition_autonomy', models.CharField(blank=True, choices=[('AUTNM', 'Autonomous'), ('FML', 'Family'), ('NTWRK', 'Network'), ('TB', 'Tube')], default=None, max_length=5, null=True, verbose_name='Sonde PEG')),
                ('diet', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Régime')),
                ('meal_on_wheels', models.BooleanField(blank=True, default=None, null=True, verbose_name='Repas sur roues')),
                ('shopping_management', models.CharField(blank=True, choices=[('AUTNM', 'Autonomous'), ('FML', 'Family'), ('NTWRK', 'Network')], default=None, max_length=5, null=True, verbose_name='Commissions à faire par')),
                ('shopping_management_desc', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Description')),
                ('urinary_incontinence', models.BooleanField(blank=True, default=None, null=True, verbose_name='Incontinence urinaire')),
                ('faecal_incontinence', models.BooleanField(blank=True, default=None, null=True, verbose_name='Incontinence fécale')),
                ('protection', models.BooleanField(blank=True, default=None, null=True, verbose_name='Protection')),
                ('day_protection', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Protection Pendant la journée')),
                ('night_protection', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Protection Pendant la nuit')),
                ('protection_ordered', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Protection à commander par')),
                ('urinary_catheter', models.BooleanField(blank=True, default=None, null=True, verbose_name='Sonde urinaire')),
                ('crystofix_catheter', models.BooleanField(blank=True, default=None, null=True, verbose_name='Crystofix')),
                ('elimination_addnl_details', models.TextField(blank=True, default=None, max_length=500, null=True, verbose_name='Autres détails ou remarques')),
                ('day_care_center', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Foyer de jour')),
                ('day_care_center_activities', models.CharField(blank=True, default=None, max_length=50, null=True, verbose_name='Activités')),
                ('household_chores', models.BooleanField(blank=True, default=None, null=True, verbose_name='Tâches domestiques')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='anamnesis_to_patient', to='invoices.patient')),
            ],
            options={
                'verbose_name': 'Anamnèse Patient',
                'verbose_name_plural': 'Anamnèses Patient',
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='ContactPerson',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('priority', models.PositiveSmallIntegerField(blank=True, default=None, null=True, verbose_name='Priorité')),
                ('contact_name', models.CharField(max_length=50, verbose_name='Nom')),
                ('contact_relationship', models.CharField(blank=True, default=None, max_length=20, null=True, verbose_name='Relation')),
                ('contact_private_phone_nbr', models.CharField(max_length=30, verbose_name='Tél. privé')),
                ('contact_business_phone_nbr', models.CharField(blank=True, default=None, max_length=30, null=True, verbose_name='Tél. bureau')),
                ('patient_anamnesis', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='contactpers_to_anamnesis', to='invoices.patientanamnesis')),
            ],
            options={
                'verbose_name': 'Personne de contact',
                'verbose_name_plural': 'Personnes de contact',
            },
        ),
        migrations.CreateModel(
            name='AssignedPhysician',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('anamnesis', models.ForeignKey(blank=True, default=None, help_text='Please enter hospitalization dates of the patient', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='patient_anamnesis', to='invoices.patientanamnesis')),
                ('assigned_physician', models.ForeignKey(blank=True, default=None, help_text='Please enter physician of the patient', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='assigned_physicians', to='invoices.physician', verbose_name='Médecin')),
            ],
            options={
                'verbose_name': 'Médecin Traitant',
                'verbose_name_plural': 'Médecins Traitants',
            },
        ),
    ]
