from django import template

register = template.Library()

#FIXME remove hardcoded profile !!!
@register.filter(name='is_company_admin')
def is_company_admin(u):
    return 'administratrice'.lower() == u.employee.occupation.name.lower()
