from dependence.careplan import CarePlanMaster


def get_active_care_plans():
    return CarePlanMaster.objects.filter(plan_end_date__isnull=True)
