from django.contrib import admin
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _

from invoices.employee import Employee


class SmartEmployeeFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('employee')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'employee'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        lookup = []
        for employee in Employee.objects.exclude(abbreviation__exact="XXX"):
            lookup.append((employee.id, employee))
        return tuple(lookup)

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        return queryset.filter(employees__id=self.value())


class EventCalendarPeriodFilter(admin.SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = _('period to display')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'period'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('week', _('week')),
            ('month', _('month')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        return queryset.filter(employees__id=self.value())

class SmartPatientFilter(admin.SimpleListFilter):
    title = _('patient')
    parameter_name = 'patient_id'

    def lookups(self, request, model_admin):
        # request is manipulated in ModelAdmin.changelist_view
        if isinstance(request, HttpRequest) and hasattr(request, "dynamic_patient_choices"):
            return request.dynamic_patient_choices
        return ()

    def queryset(self, request, queryset):
        # Handle empty or invalid filter values
        value = self.value()
        if value is None:
            return queryset  # No filtering
        try:
            if self.value():
                return queryset.filter(patient_id=self.value())
            else:
                return queryset
        except (ValueError, TypeError):
            return queryset  # Return the original queryset if the value is invalid

class DistanceMatrixSmartPatientFilter(admin.SimpleListFilter):
    title = _('patient')
    parameter_name = 'patient_origin_id'

    def lookups(self, request, model_admin):
        # request is manipulated in ModelAdmin.changelist_view
        if isinstance(request, HttpRequest) and hasattr(request, "dynamic_patient_choices"):
            return request.dynamic_patient_choices
        return ()

    def queryset(self, request, queryset):
        # Handle empty or invalid filter values
        value = self.value()
        if value is None:
            return queryset  # No filtering
        try:
            if self.value():
                return queryset.filter(patient_id=self.value())
            else:
                return queryset
        except (ValueError, TypeError):
            return queryset  # Return the original queryset if the value is invalid

class SmartMedicalPrescriptionFilter(admin.SimpleListFilter):
    title = _('medical prescription')
    parameter_name = 'medical_prescription_id'

    def lookups(self, request, model_admin):
        # request is manipulated in ModelAdmin.changelist_view
        if isinstance(request, HttpRequest) and hasattr(request, "dynamic_medical_prescription_choices"):
            return request.dynamic_medical_prescription_choices
        return ()

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(prescriptions__medical_prescription__id=self.value())
        else:
            return queryset
