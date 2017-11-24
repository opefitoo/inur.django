from django.forms import ModelForm, ChoiceField, ModelChoiceField

from invoices.models import Prestation
from invoices.timesheet import Employee


class PrestationForm(ModelForm):
    class Meta:
        model = Prestation
        fields = ('employee',)
