from django import template

register = template.Library()

#FIXME remove hardcoded profile !!!
@register.filter(name='is_company_admin')
def is_company_admin(u):
    if u.employee.occupation.name.lower() in ['administrateur', 'administratrice']:
        return True

@register.filter(name='selected_labels')
def selected_labels(instance, field):
    return [label for value, label in instance._meta.get_field(field).temp_choices if value in getattr(instance, field)]  
