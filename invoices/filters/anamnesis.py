from django.contrib import admin
from django.utils.translation import gettext_lazy as _

class DeceasedFilter(admin.SimpleListFilter):
    title = _('status vie/mort')
    parameter_name = 'is_deceased'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Décédé')),
            ('no', _('En vie')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(patient__date_of_death__isnull=False)
        if self.value() == 'no':
            return queryset.filter(patient__date_of_death__isnull=True)

class ClientLeftFilter(admin.SimpleListFilter):
    title = _('status client')
    parameter_name = 'is_client_left'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Parti')),
            ('no', _('Actif')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            # or patient is deceased
            return queryset.filter(patient__date_of_exit__isnull=False) | queryset.filter(patient__date_of_death__isnull=False)
        if self.value() == 'no':
            return queryset.filter(patient__date_of_exit__isnull=True) & queryset.filter(patient__date_of_death__isnull=True)

