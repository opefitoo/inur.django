from dataclasses import fields
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet
from django.core.validators import EMPTY_VALUES
from django import forms
from dependence.enums.falldeclaration_enum import FallCircumstances, FallCognitiveMoodDiorders, FallConsequences, FallIncontinences, FallRequiredMedicalActs

from dependence.falldeclaration import FallDeclaration
from django.utils.translation import gettext_lazy as _

class TypeDescriptionGenericInlineFormset(BaseInlineFormSet):

    def clean(self):
        if hasattr(self, 'cleaned_data'):
            elms = []
            for cln_data in self.cleaned_data:
                if len(cln_data) == 0:
                    continue
                elm = cln_data['habit_type']
                elms.append(elm)
                if elms.count(elm) > 1:
                    raise ValidationError('Seulement un %s à la fois' % elm)


class TensionAndTemperatureParametersFormset(BaseInlineFormSet):

    def clean(self):
        super(TensionAndTemperatureParametersFormset, self).clean()
        if hasattr(self, 'cleaned_data'):
            rowindex = 0
            for row in self.cleaned_data:
                rowindex += 1
                if 'oximeter_saturation' in row and row['oximeter_saturation'] and not row['DELETE']:
                    self.validate_saturation(rowindex, row)
                if 'params_date_time' in row and row['params_date_time'] and not row['DELETE']:
                    self.validate_periods(rowindex, self.data['params_month'], self.data['params_year'], row)


    @staticmethod
    def validate_saturation(rowindex, data):
        is_valid = (100 >= data['oximeter_saturation'] > 0) or data['oximeter_saturation'] is None
        if not is_valid:
            raise ValidationError("Ligne %s : Valeure incorrecte pour la saturation - doit être entre 0 et 100" % rowindex)

    @staticmethod
    def validate_periods(rowindex, month, year, data):
        is_valid = data['params_date_time'].month == int(month) and data['params_date_time'].year == int(year)
        if not is_valid:
            raise ValidationError("Ligne %d : Date doit être dans le mois %s de l'année %s" % (rowindex, month, year))

class FallDeclarationForm(forms.ModelForm):
    class Meta:
        model = FallDeclaration
        exclude = ()
        fields = (
                'fall_consequences',
                'fall_required_medical_acts',
                'fall_cognitive_mood_diorders',
                'fall_incontinences',
            )
        
    fall_consequences = forms.MultipleChoiceField(choices=FallConsequences.choices,
                 widget=forms.CheckboxSelectMultiple(),
                 required = False,)    
    fall_required_medical_acts = forms.MultipleChoiceField(choices=FallRequiredMedicalActs.choices, 
                widget=forms.CheckboxSelectMultiple(),
                required = False, )
    fall_cognitive_mood_diorders = forms.MultipleChoiceField(choices=FallCognitiveMoodDiorders.choices,
                widget=forms.CheckboxSelectMultiple(),
                required = False,)
    fall_incontinences = forms.MultipleChoiceField(choices=FallIncontinences.choices,
                widget=forms.CheckboxSelectMultiple(),
                required = False,)
    def clean(self):
        fall_circumstance = self.cleaned_data.get('fall_circumstance', None)
        activity_name = self.cleaned_data.get('other_fall_circumstance', None)
        if fall_circumstance == FallCircumstances.FCI_OTHER_CAUSES:
            if activity_name in EMPTY_VALUES:
                self._errors['other_fall_circumstance'] = self.error_class([
                    _("Depending on your selection, you must fill in the field: \"Other circumstances of the fall\"")])
        else:
            if activity_name not in EMPTY_VALUES:
                self._errors['other_fall_circumstance'] = self.error_class([
                    _("Depending on your selection, you must leave the \"Other circumstances of the fall\" field empty")])

        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super(FallDeclarationForm, self).__init__(*args, **kwargs)
        self.initial['fall_consequences'] = eval(self.initial['fall_consequences'])    
        self.initial['fall_required_medical_acts'] = eval(self.initial['fall_required_medical_acts'])    
        self.initial['fall_cognitive_mood_diorders'] = eval(self.initial['fall_cognitive_mood_diorders'])    
        self.initial['fall_incontinences'] = eval(self.initial['fall_incontinences'])    
