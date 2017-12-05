from dal import autocomplete
from django.db.models import Q

from invoices.models import CareCode, Prestation, Patient
from invoices.timesheet import Employee


def get_queryset_filter(query_str, fields):
    filter_qs = Q()
    for search_field in fields:
        query = Q(**{"%s__icontains" % search_field: query_str})
        filter_qs = filter_qs | query

    return filter_qs


class CareCodeAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return CareCode.objects.none()

        qs = CareCode.objects.all()
        at_home = self.forwarded.get('at_home', False)
        if at_home:
            qs = qs.filter(code=Prestation.AT_HOME_CARE_CODE)

        if self.q:
            filter_qs = get_queryset_filter(self.q, CareCode.autocomplete_search_fields())
            qs = qs.filter(filter_qs)

        return qs


class PatientAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return Patient.objects.none()

        qs = Patient.objects.all()
        is_private = self.forwarded.get('is_private', False)
        if is_private:
            qs = qs.filter(is_private=is_private)

        if self.q:
            filter_qs = get_queryset_filter(self.q, Patient.autocomplete_search_fields())
            qs = qs.filter(filter_qs)

        return qs


class EmployeeAutocomplete(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        if not self.request.user.is_authenticated():
            return Employee.objects.none()

        qs = Employee.objects.all()

        if self.q:
            filter_qs = get_queryset_filter(self.q, Employee.autocomplete_search_fields())
            qs = qs.filter(filter_qs)

        return qs
