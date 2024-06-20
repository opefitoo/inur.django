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

class UnderHeatWaveRiskFilter(admin.SimpleListFilter):
    title = _('Under Heat Wave Risk')
    parameter_name = 'under_heat_wave_risk'

    def lookups(self, request, model_admin):
        return (
            ('>75', _('Older than 75')),
            ('<=75', _('75 or younger')),
            ('unknown', _('Unknown Age')),
        )

    def queryset(self, request, queryset):
        if self.value() == '>75':
            return queryset.filter(pk__in=[patient.pk for patient in queryset if patient.age is not None and patient.age > 75])
        if self.value() == '<=75':
            return queryset.filter(pk__in=[patient.pk for patient in queryset if patient.age is not None and patient.age <= 75])
        if self.value() == 'unknown':
            return queryset.filter(pk__in=[patient.pk for patient in queryset if patient.age is None])
        return queryset

class IsPatientDeceasedFilter(admin.SimpleListFilter):
    title = _('Is Patient Deceased')
    parameter_name = 'is_patient_deceased'

    def lookups(self, request, model_admin):
        return (
            ('yes', _('Yes')),
            ('no', _('No')),
        )

    # only if date_of_death is not null
    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(date_of_death__isnull=False)
        elif self.value() == 'no':
            return queryset.filter(date_of_death__isnull=True)
