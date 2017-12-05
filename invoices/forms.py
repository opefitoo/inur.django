from django.forms import BaseInlineFormSet, ValidationError, ModelChoiceField, ModelForm

from invoices.models import Prestation, CareCode, InvoiceItem, Patient
from invoices.timesheet import Employee
from invoices.widgets import AutocompleteModelSelect2CustomWidget


class ValidityDateFormSet(BaseInlineFormSet):
    def clean(self):
        super(ValidityDateFormSet, self).clean()

        if hasattr(self, 'cleaned_data'):
            for row_index, row_data in enumerate(self.cleaned_data):
                is_valid = True
                for index, data in enumerate(self.cleaned_data):
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
                    raise ValidationError('Validity Dates periods should not intersect')


class PrestationForm(ModelForm):
    carecode = ModelChoiceField(
        queryset=CareCode.objects.all(),
        widget=AutocompleteModelSelect2CustomWidget(url='carecode-autocomplete', forward=['at_home'])
    )
    employee = ModelChoiceField(
        queryset=Employee.objects.all(),
        required=False,
        widget=AutocompleteModelSelect2CustomWidget(url='employee-autocomplete')
    )

    def __init__(self, *args, **kwargs):
        super(PrestationForm, self).__init__(*args, **kwargs)
        self.fields['carecode'].autocomplete = False
        self.fields['employee'].autocomplete = False

    class Meta:
        model = Prestation
        fields = '__all__'


class InvoiceItemForm(ModelForm):
    patient = ModelChoiceField(
        queryset=Patient.objects.all(),
        widget=AutocompleteModelSelect2CustomWidget(url='patient-autocomplete', forward=['is_private'])
    )

    def __init__(self, *args, **kwargs):
        super(InvoiceItemForm, self).__init__(*args, **kwargs)
        self.fields['patient'].autocomplete = False

    class Meta:
        model = InvoiceItem
        fields = '__all__'
