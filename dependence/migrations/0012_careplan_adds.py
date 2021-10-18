# Written by @mehdi

from django.conf import settings
from django.db import migrations


def insert_user_one(apps, schema_editor):
    user_model = apps.get_model("auth", "User")
    user_1 = user_model.objects.get(id=1)
    careplan_master_model = apps.get_model("dependence", "CarePlanMaster")
    careplans = careplan_master_model.objects.all()
    for c in careplans:
        c.user = user_1
        c.save()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('dependence', '0011_careplan_adds'),
    ]

    operations = [
        migrations.RunPython(insert_user_one),
    ]
