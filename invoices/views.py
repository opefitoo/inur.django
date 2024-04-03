# from dal import autocomplete
from django.contrib.auth import authenticate, login
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.signals import user_logged_in
from django.db.models import Q
from django.dispatch import receiver
from django.http import Http404, HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.template import loader
from django.views import View
from django.views.decorators.http import require_POST
from rest_framework.authtoken.models import Token

from invoices.models import Prestation, MedicalPrescription, InvoiceItem
from invoices.resources import Car
from invoices.utils import get_git_hash


@receiver(user_logged_in)
def create_auth_token(sender, user, request, **kwargs):
    token, created = Token.objects.get_or_create(user=user)
    request.session['auth_token'] = token.key
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            token, created = Token.objects.get_or_create(user=user)
            request.session['auth_token'] = token.key
            response = redirect('admin:index')
            response.set_cookie('auth_token', token.key)  # Set the token as a cookie
            return response
    return render(request, 'admin/login.html')
class LockCarView(View):
    def get(self, request, *args, **kwargs):
        car = Car.objects.get(pk=kwargs['pk'])
        # Code to lock the car goes here
        return JsonResponse({'status': 'success'})

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


def robots_view(request):
    template = loader.get_template('robots.txt')
    return HttpResponse(template.render(), content_type='text/plain')

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
