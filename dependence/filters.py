# In `dependence/admin.py`

from django.contrib import admin

from invoices.models import SubContractor


class SubContractorFilter(admin.SimpleListFilter):
    title = 'Subcontractor'
    parameter_name = 'subcontractor'

    def lookups(self, request, model_admin):
        subcontractors = SubContractor.objects.all()
        return [(sub.id, sub.get_abbreviated_name()) for sub in subcontractors]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                invoice_line__subcontractor_id=self.value()
            ).distinct() | queryset.filter(
                invoice_item__subcontractor_id=self.value()
            ).distinct()
        return queryset
