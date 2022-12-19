# from dal import autocomplete
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import Http404, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_POST

from invoices.forms import YaleConfigurationForm
from invoices.models import Prestation, MedicalPrescription, InvoiceItem
from invoices.yale.api import CustomizedYaleSession


def get_queryset_filter(query_str, fields):
    filter_qs = Q()
    for search_field in fields:
        query = Q(**{"%s__icontains" % search_field: query_str})
        filter_qs = filter_qs | query

    return filter_qs


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


def load_prescriptions(request):
    patient_name = request.GET.get('patient_name')
    value = request.GET.get('selected_medical_prescription_id')
    medical_prescriptions = MedicalPrescription.objects.filter(patient__name__startswith=patient_name.split(' ')[0],
                                                               patient__first_name__endswith=patient_name.split(' ')[-1]
                                                               )
    # [(None, [{'name': 'medical_prescription', 'value': '', 'label': '---------', 'selected': False, 'index': '0', 'attrs': {}, 'type': 'select', 'template_name': 'django/forms/widgets/select_option.html', 'wrap_label': True}], 0),
    #  (None, [{'name': 'medical_prescription', 'value': <django.forms.models.ModelChoiceIteratorValue object at 0x12cf6a5b0>, 'label': 'RISCHETTE René (2022-07-07) sans fichier', 'selected': False, 'index': '1', 'attrs': {}, 'type': 'select', 'template_name': 'django/forms/widgets/select_option.html', 'wrap_label': True}], 1),
    #  (None, [{'name': 'medical_prescription', 'value': <django.forms.models.ModelChoiceIteratorValue object at 0x12cf66af0>, 'label': 'LEE Paul (2019-11-06) [CHRIS...]', 'selected': True, 'index': '2', 'attrs': {'selected': True}, 'type': 'select', 'template_name': 'django/forms/widgets/select_option.html', 'wrap_label': True}], 2)]
    widget_optgroups = []
    index = 1
    for medical_prescription in medical_prescriptions:
        if medical_prescription.pk == int(selected_medical_prescription_id):
            selected = True
        else:
            selected = False
        widget_optgroups.append((None, [{'name': 'medical_prescription',
                                         'value': medical_prescription,
                                         'label': str(medical_prescription),
                                         'selected': selected,
                                         'index': str(index),
                                         'attrs': {'selected': False},
                                         'type': 'select',
                                         'template_name': 'django/forms/widgets/select_option.html',
                                         'wrap_label': True}],
                                 index))
        index += 1

    for k, y, v in widget_optgroups:
        print(k)
        print(y)
        print(v)

    # return render(request, 'widgets/select-medical-prescription.html',
    #               {'widget_optgroups': widget_optgroups})


    return render(request, 'widgets/select-medical-prescription.html',
                  {'widget': {'optgroups': medical_prescriptions}}
                  )
    # return JsonResponse(list(cities.values('id', 'name')), safe=False)


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
@login_required
def yale_configuration_view(request):
    yale_session = CustomizedYaleSession
    message = None
    if request.method == 'POST':
        form = YaleConfigurationForm(request.POST)
        if form.validate():
            input_value = form.text_input.data
            if form.send_button.data:
                # send input value to REST service
                authenticator = yale_session.send_validation()
                message = "Sent to yale %s" % authenticator
            elif form.validate_button.data:
                yale_session.authenticate(input_value)
            elif form.house_activities_button.data:
                house_activities =  yale_session.get_house_activities()
                message = "House activities %s" % house_activities
            elif form.display_state_button.data:
                message = yale_session.get_authentication_state()
    else:
        form = YaleConfigurationForm()
    return render(request, 'yale/yale_configuration_template.html', {'form': form, 'message': message})
