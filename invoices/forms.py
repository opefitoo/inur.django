from django.forms import BaseInlineFormSet, ValidationError, ModelChoiceField, ModelForm
from django import forms
from datetime import datetime

from invoices.models import Prestation, CareCode, InvoiceItem, Patient, MedicalPrescription
from invoices.timesheet import Employee
from invoices.widgets import AutocompleteModelSelect2CustomWidget, CustomAdminSplitDateTime


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


class PrestationForm(ModelForm):
    carecode = ModelChoiceField(
        queryset=CareCode.objects.all(),
        widget=AutocompleteModelSelect2CustomWidget(url='carecode-autocomplete')
    )
    employee = ModelChoiceField(
        queryset=Employee.objects.all(),
        required=False,
        widget=AutocompleteModelSelect2CustomWidget(url='employee-autocomplete')
    )
    at_home_paired = ModelChoiceField(
        queryset=Prestation.objects.all(),
        required=False,
        widget=forms.HiddenInput()
    )
    
    at_home_paired_name = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), disabled=True,
                                          required=False)
    paired_at_home_name = forms.CharField(widget=forms.TextInput(attrs={'readonly': 'readonly'}), disabled=True,
                                          required=False)

    def __init__(self, *args, **kwargs):
        super(PrestationForm, self).__init__(*args, **kwargs)
        self.fields['carecode'].autocomplete = False
        self.fields['employee'].autocomplete = False
        self.fields['date'].widget = CustomAdminSplitDateTime()

        if self.instance.at_home_paired is not None:
            self.fields['carecode'].disabled = True
            self.fields['at_home'].disabled = True
        if hasattr(self.instance, 'paired_at_home') and self.instance.paired_at_home is not None:
            self.fields['at_home'].disabled = True
            self.fields['at_home_paired_name'].widget = forms.HiddenInput()
            self.fields['paired_at_home_name'].initial = self.instance.paired_at_home_name
        elif hasattr(self.instance, 'at_home_paired') and self.instance.at_home_paired is not None:
            self.fields['at_home'].disabled = True
            self.fields['paired_at_home_name'].widget = forms.HiddenInput()
            self.fields['at_home_paired_name'].initial = self.instance.at_home_paired_name
        else:
            self.fields['at_home_paired_name'].widget = forms.HiddenInput()
            self.fields['paired_at_home_name'].widget = forms.HiddenInput()

    class Meta:
        model = Prestation
        fields = '__all__'


class InvoiceItemForm(ModelForm):
    patient = ModelChoiceField(
        queryset=Patient.objects.all(),
        widget=AutocompleteModelSelect2CustomWidget(url='patient-autocomplete', forward=['is_private'])
    )

    medical_prescription = ModelChoiceField(
        queryset=MedicalPrescription.objects.all(),
        widget=AutocompleteModelSelect2CustomWidget(url='medical-prescription-autocomplete', forward=['patient']),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super(InvoiceItemForm, self).__init__(*args, **kwargs)
        self.fields['patient'].autocomplete = False
        self.fields['medical_prescription'].autocomplete = False

    class Meta:
        model = InvoiceItem
        fields = '__all__'


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
