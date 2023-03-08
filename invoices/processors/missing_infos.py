from django.apps import apps
from django.db.models import  Q

default_app_label='invoices'
default_manadatory_fields = [
    ('employee','driving_licence_number')
]

def search_for_missing_manadatory_infos(manadatory_fields = default_manadatory_fields):
    for field_info in manadatory_fields:
        field_model = field_info[0]
        field_name = field_info[1]
        records_with_missing_infos = search_for_missing_manadatory_infos_for_field(field_model, field_name)
        print(records_with_missing_infos)

    return 'not working yet'

def search_for_missing_manadatory_infos_for_field(field_model, field_name, app_label=default_app_label):
    my_model = apps.get_model(app_label,model_name=field_model)
    field_name_isnull = field_name+'__isnull'
    srch = my_model.objects.filter(Q(**{field_name_isnull:True}) | Q(**{field_name:''}))
    return srch