from django.contrib import admin
from django.utils.translation import gettext_lazy as _


class UnderAssuranceDependanceFilter(admin.SimpleListFilter):
    title = _('Under Assurance Dependance')
    parameter_name = 'under_assurance_dependance'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Yes')),
            ('no', _('No')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(patient__is_under_dependence_insurance=True)
        elif self.value() == 'no':
            return queryset.filter(patient__is_under_dependence_insurance=False)
