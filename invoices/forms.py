from datetime import datetime

from constance import config
from dal import autocomplete
from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.forms import BaseInlineFormSet, ValidationError, ModelForm, ModelMultipleChoiceField

from invoices.employee import Employee
from invoices.events import Event, create_or_update_google_calendar
from invoices.models import InvoiceItem, MedicalPrescription
from invoices.timesheet import SimplifiedTimesheet, SimplifiedTimesheetDetail
from invoices.widgets import CodeSnWidget


def check_for_periods_intersection(cleaned_data):
    for row_index, row_data in enumerate(cleaned_data):
        is_valid = True
        for index, data in enumerate(cleaned_data):
            if index == row_index:
                continue

            if row_data['start_date'] >= data['start_date'] and data['end_date'] is None:
                is_valid = False
            elif data['end_date'] is not None:
                if data['start_date'] <= row_data['start_date'] <= data['end_date']:
                    is_valid = False
                if row_data['end_date'] is not None:
                    if data['start_date'] <= row_data['end_date'] <= data['end_date']:
                        is_valid = False

        if not is_valid:
            raise ValidationError('Dates periods should not intersect')


def check_for_periods_intersection_time_based(cleaned_data):
    extra_cleaned_data = list(filter(None, cleaned_data))
    for row_index, row_data in enumerate(extra_cleaned_data):
        is_valid = True
        dates_on_error = set()
        for index, data in enumerate(extra_cleaned_data):
            if index == row_index:
                continue
            elif row_data['start_date'].date() != data['start_date'].date():
                continue
            elif row_data['DELETE']:
                continue
            elif not (row_data['start_date'].time() > data['end_date']
                      or row_data['end_date'] < data['start_date'].time()):
                dates_on_error.add(data['start_date'].date().strftime("%Y-%m-%d"))
                is_valid = False

        if not is_valid:
            raise ValidationError('Dates periods should not intersect : %s' % dates_on_error)


class ValidityDateFormSet(BaseInlineFormSet):
    def clean(self):
        super(ValidityDateFormSet, self).clean()

        if hasattr(self, 'cleaned_data'):
            check_for_periods_intersection(self.cleaned_data)


class PrestationInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super(PrestationInlineFormSet, self).clean()
        if hasattr(self, 'cleaned_data'):
            self.validate_max_limit(self.cleaned_data)

    @staticmethod
    def validate_max_limit(cleaned_data):
        expected_count = 0
        at_home_added = False
        for row_data in cleaned_data:
            if 'DELETE' in row_data and row_data['DELETE']:
                expected_count -= 1
            else:
                expected_count += 1
                if not at_home_added and 'at_home' in row_data and row_data['at_home']:
                    at_home_added = True
                    expected_count += 1

        if expected_count > InvoiceItem.PRESTATION_LIMIT_MAX:
            message = "Max number of Prestations for one InvoiceItem is %s" % (str(InvoiceItem.PRESTATION_LIMIT_MAX))
            raise ValidationError(message)


class SimplifiedTimesheetForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.timesheet_validated:
            for k, v in self.fields.items():
                v.disabled = True

    class Meta:
        model = SimplifiedTimesheet
        fields = '__all__'


class SimplifiedTimesheetDetailForm(BaseInlineFormSet):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(self.instance, 'simplified_timesheet') and self.instance.simplified_timesheet.timesheet_validated:
            for k, v in self.fields.items():
                v.disabled = True

    class Meta:
        model = SimplifiedTimesheetDetail
        fields = '__all__'

    def clean(self):
        super(SimplifiedTimesheetDetailForm, self).clean()
        all_clean_data = []
        for form in self.forms:
            if len(form.errors) == 0:
                all_clean_data.append(form.cleaned_data)
        check_for_periods_intersection_time_based(all_clean_data)


# class PrestationForm(ModelForm):
#     carecode = ModelChoiceField(
#         queryset=CareCode.objects.all(),
#         widget=ModelSelect2(url='carecode-autocomplete')
#     )
#     employee = ModelChoiceField(
#         queryset=Employee.objects.all(),
#         required=False,
#         widget=ModelSelect2(url='employee-autocomplete')
#     )
#     at_home_paired = ModelChoiceField(
#         queryset=Prestation.objects.all(),
#         required=False,
#         widget=forms.HiddenInput()
#     )
#
#     at_home_paired_name = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), disabled=True,
#                                           required=False)
#     paired_at_home_name = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), disabled=True,
#                                           required=False)
#
#     def __init__(self, *args, **kwargs):
#         super(PrestationForm, self).__init__(*args, **kwargs)
#         self.fields['carecode'].autocomplete = False
#         self.fields['employee'].autocomplete = False
#         self.fields['date'].widget = CustomAdminSplitDateTime()
#
#         if self.instance.at_home_paired is not None:
#             self.fields['carecode'].disabled = True
#             self.fields['at_home'].disabled = True
#         if hasattr(self.instance, 'paired_at_home') and self.instance.paired_at_home is not None:
#             self.fields['at_home'].disabled = True
#             self.fields['at_home_paired_name'].widget = forms.HiddenInput()
#             self.fields['paired_at_home_name'].initial = self.instance.paired_at_home_name
#         elif hasattr(self.instance, 'at_home_paired') and self.instance.at_home_paired is not None:
#             self.fields['at_home'].disabled = True
#             self.fields['paired_at_home_name'].widget = forms.HiddenInput()
#             self.fields['at_home_paired_name'].initial = self.instance.at_home_paired_name
#         else:
#             self.fields['at_home_paired_name'].widget = forms.HiddenInput()
#             self.fields['paired_at_home_name'].widget = forms.HiddenInput()
#
#     class Meta:
#         model = Prestation
#         fields = '__all__'


class InvoiceItemForm(forms.ModelForm):
    medical_prescription = forms.ModelChoiceField(
        help_text='Veuillez choisir une ordonnance',
        queryset=MedicalPrescription.objects.all(),
        widget=autocomplete.ModelSelect2(url='medical-prescription-autocomplete',
                                         attrs={'data-placeholder': '...'},
                                         forward=['patient']),
        required=False,
    )

    #
    # def __init__(self, *args, **kwargs):
    #     super(InvoiceItemForm, self).__init__(*args, **kwargs)
    #     if self.instance.has_patient():
    #         self.fields['medical_prescription'].queryset = MedicalPrescription.objects.filter(patient=self.instance.patient)
    class Meta:
        model = InvoiceItem
        fields = '__all__'
        # widgets = {
        #     'medical_prescription': dal.autocomplete.ModelSelect2(url='medical-prescription-autocomplete',
        #                                                           attrs={'data-placeholder': '...',
        #                                                                  'data-minimum-input-length': 3},
        #                                                           forward=['patient'])
        # }


class HospitalizationFormSet(BaseInlineFormSet):
    def clean(self):
        super(HospitalizationFormSet, self).clean()

        if hasattr(self, 'cleaned_data'):
            check_for_periods_intersection(self.cleaned_data)
            if 'date_of_death' in self.data and self.data['date_of_death']:
                date_of_death = datetime.strptime(self.data['date_of_death'], "%Y-%m-%d").date()
                self.validate_with_patient_date_of_death(self.cleaned_data, date_of_death)

    @staticmethod
    def validate_with_patient_date_of_death(cleaned_data, date_of_death):
        for row_data in cleaned_data:
            if row_data['end_date'] >= date_of_death:
                raise ValidationError("Hospitalization cannot be later than or include Patient's death date")


class PatientForm(ModelForm):
    code_sn = forms.CharField(widget=CodeSnWidget())

    def __init__(self, *args, **kwargs):
        super(PatientForm, self).__init__(*args, **kwargs)


class EmployeeSelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        if value:
            option['attrs']['data-abbreviation'] = value.instance.abbreviation
        return option


class EventForm(ModelForm):
    # event_employees = ModelMultipleChoiceField(
    #     Employee.objects.filter(end_contract__isnull=True).exclude(abbreviation="XXX").order_by('-abbreviation'),
    #     widget=FilteredSelectMultiple("employees", is_stacked=True, ))

    class Meta:
        model = Event
        exclude = []

    def __init__(self, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        if self.instance.at_office:
            self.fields['event_address'].disabled = True

    #
    # def clean(self):
    #     cleaned_data = super().clean()
    #     if cleaned_data.get('event_employees'):
    #         self.instance.event_employees.set(cleaned_data.get('event_employees').all())
    #         self.instance.save

    #     if cleaned_data.get('at_office'):
    #         cleaned_data['event_address'] = "%s %s" % (config.NURSE_ADDRESS, config.NURSE_ZIP_CODE_CITY)
    #     cal = create_or_update_google_calendar(cleaned_data)
    #     self.calendar_id = cal.get('id')
    #     self.calendar_url = cal.get('htmlLink')
    #     messages = self.validate(self, self.id, self.__dict__)
    #     if messages:
    #         raise ValidationError(messages)
