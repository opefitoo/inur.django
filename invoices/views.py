# from dal import autocomplete
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST

from invoices.models import Prestation, MedicalPrescription, InvoiceItem
from invoices.utils import get_git_hash


def password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            if user.email is not None:
                user.email = "None"
                user.save()
            update_session_auth_hash(request, user)
            return redirect('home')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'password_change.html', {'form': form})
def get_queryset_filter(query_str, fields):
    filter_qs = Q()
    for search_field in fields:
        query = Q(**{"%s__icontains" % search_field: query_str})
        filter_qs = filter_qs | query

    return filter_qs


def home_view(request):
    context = {
        'git_hash': get_git_hash(),
    }
    return render(request, 'home.html', context)


# class CareCodeAutocomplete(autocomplete.Select2QuerySetView):
#     def get_queryset(self):
#         if not self.request.user.is_authenticated:
#             return CareCode.objects.none()
#
#         qs = CareCode.objects.all()
#         at_home = self.forwarded.get('at_home', False)
#         if at_home:
#             qs = qs.filter(code=Prestation.AT_HOME_CARE_CODE)
#
#         if self.q:
#             filter_qs = get_queryset_filter(self.q, CareCode.autocomplete_search_fields())
#             qs = qs.filter(filter_qs)
#
#         return qs


# class PatientAutocomplete(autocomplete.Select2QuerySetView):
#     def get_queryset(self):
#         if not self.request.user.is_authenticated:
#             return Patient.objects.none()
#
#         qs = Patient.objects.all()
#         is_private = self.forwarded.get('is_private', False)
#         if is_private:
#             qs = qs.filter(is_private=is_private)
#
#         if self.q:
#             filter_qs = get_queryset_filter(self.q, Patient.autocomplete_search_fields())
#             qs = qs.filter(filter_qs)
#
#         return qs
#
#
# class MedicalPrescriptionAutocomplete(autocomplete.Select2QuerySetView):
#     def get_queryset(self):
#         if not self.request.user.is_authenticated:
#             return MedicalPrescription.objects.none()
#
#         qs = MedicalPrescription.objects.all()
#         patient = self.forwarded.get('patient', False)
#         if patient:
#             qs = qs.filter(patient=patient)
#
#         if self.q:
#             filter_qs = get_queryset_filter(self.q, MedicalPrescription.autocomplete_search_fields())
#             qs = qs.filter(filter_qs)
#
#         return qs


#
#
# class EmployeeAutocomplete(autocomplete.Select2QuerySetView):
#     def get_queryset(self):
#         if not self.request.user.is_authenticated:
#             return Employee.objects.none()
#
#         qs = Employee.objects.all()
#
#         if self.q:
#             filter_qs = get_queryset_filter(self.q, Employee.autocomplete_search_fields())
#             qs = qs.filter(filter_qs)
#
#         return qs


@require_POST
def delete_prestation(request):
    prestation_id = request.POST.get('prestation_id', None)
    if request.method != "POST" or prestation_id is None or not request.user.has_perm('invoices.delete_prestation'):
        raise Http404

    prestation = Prestation.objects.get(pk=prestation_id)
    prestation.delete()

    return JsonResponse({'status': 'Success'})


def optgroups(self, name, value, attr=None):
    """Return selected options based on the ModelChoiceIterator."""
    default = (None, [], 0)
    groups = [default]
    has_selected = False
    selected_choices = {
        str(v) for v in value if str(v) not in self.choices.field.empty_values
    }
    if not self.is_required and not self.allow_multiple_selected:
        default[1].append(self.create_option(name, "", "", False, 0))
    remote_model_opts = InvoiceItem.medical_prescription.model._meta
    to_field_name = getattr(
        InvoiceItem.medical_prescription, "field_name", MedicalPrescription.pk.attname
    )
    to_field_name = MedicalPrescription.get_field(to_field_name).attname
    choices = (
        (getattr(obj, to_field_name), self.choices.field.label_from_instance(obj))
        for obj in self.choices.queryset.using(self.db).filter(
        **{"%s__in" % to_field_name: selected_choices}
    )
    )
    for option_value, option_label in choices:
        selected = str(option_value) in value and (
                has_selected is False or self.allow_multiple_selected
        )
        has_selected |= selected
        index = len(default[1])
        subgroup = default[1]
        subgroup.append(
            self.create_option(
                name, option_value, option_label, selected_choices, index
            )
        )
    return groups
