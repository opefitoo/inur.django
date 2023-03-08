from django.apps import apps
from django.db.models import  Q
from django.urls import reverse

DEFAULT_APP_LABEL = 'invoices'
DEFAULT_MANADATORY_FIELDS = [
    ('employee','driving_licence_number')
]
BASE_URL = 'http://127.0.0.1:8000'

def search_for_missing_manadatory_infos(manadatory_fields = DEFAULT_MANADATORY_FIELDS, app_label=DEFAULT_APP_LABEL):
    rslt=[]
    for field_info in manadatory_fields:
        field_model = field_info[0]
        field_name = field_info[1]
        records_with_missing_infos = search_for_missing_manadatory_infos_for_field(field_model, field_name, app_label)
        field_verbose_name = records_with_missing_infos.model._meta.get_field(field_name)._verbose_name
        field_model_verbose_name = records_with_missing_infos.model._meta.verbose_name
        for rec in records_with_missing_infos:
            field_instance_id = rec.__str__()
            message = "The %s identified by \"%s\" is missing the following info: \"%s\"" % \
                (field_model_verbose_name,field_instance_id,field_verbose_name)
            rslt.append(message)
            info = (app_label, field_model)
            rec_admin_url = reverse('admin:%s_%s_change' % info, args=(rec.pk,))
            message_for_link = "You can update the missing info bu following the link %s%s" % (BASE_URL,rec_admin_url)
            rslt.append(message_for_link)
        

    return rslt

def search_for_missing_manadatory_infos_for_field(field_model, field_name, app_label):
    my_model = apps.get_model(app_label,model_name=field_model)
    field_name_isnull = field_name+'__isnull'
    srch = my_model.objects.filter(Q(**{field_name_isnull:True}) | Q(**{field_name:''}))
    return srch