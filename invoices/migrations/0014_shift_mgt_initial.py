# Generated by Django 4.2.8 on 2023-12-24 19:04

from django.db import migrations, models
import django.db.models.deletion
import invoices.actions.helpers
import invoices.models


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0013_add_flags_on_invoice'),
    ]

    operations = [
        migrations.CreateModel(
            name='Shift',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
            ],
        ),
        migrations.AddField(
            model_name='employee',
            name='by_pass_shifts',
            field=models.BooleanField(default=False, verbose_name='Bypass shifts'),
        ),
        migrations.AlterField(
            model_name='bedsoreevaluation',
            name='image',
            field=models.ImageField(upload_to=invoices.actions.helpers.update_bedsore_pictures_filenames, validators=[invoices.models.validate_image]),
        ),
        migrations.CreateModel(
            name='EmployeeShift',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='invoices.employee')),
                ('shift', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='invoices.shift')),
            ],
        ),
    ]