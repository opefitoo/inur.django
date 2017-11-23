from ajax_select.fields import AutoCompleteSelectField
from django.forms import ModelForm


class PrestationForm(ModelForm):
    carecode = AutoCompleteSelectField('carecode')
    employee = AutoCompleteSelectField('employee')
