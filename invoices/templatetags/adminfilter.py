from django import template

register = template.Library()

#FIXME remove hardcoded profile !!!
@register.filter(name='is_company_admin')
def is_company_admin(u):
    return 'administratrice'.lower() == u.employee.occupation.name.lower()

@register.filter(name='selected_labels')
def selected_labels(instance, field):
    return [label for value, label in instance._meta.get_field(field).choices if value in getattr(instance, field)]  