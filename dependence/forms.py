from dataclasses import fields
from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet
from django.core.validators import EMPTY_VALUES
from django import forms
from dependence.enums.falldeclaration_enum import FallCircumstances

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

        inline_fields=(
                       'fall_consequences',
                       'fall_required_medical_acts',
                       'fall_cognitive_mood_diorders',
                       'fall_incontinences'
                       )
        inline_fields_display=(
                       _("Consequences of the fall"),
                       _("Medical and/or nursing acts required within 24 hours"),
                       _("Cognitive and/or mood disorders"),
                       _("Incontinence")
                        )               
        inline_fields_name=(
                       'consequence',
                       'required_medical_act',
                       'cognitive_mood_diorder',
                       'incontinence'
                        )               
        for idx,field in enumerate(inline_fields):               
            value_count = int(self.data.get(field+'-TOTAL_FORMS', 0))
            temp = []
            for i in range(0, value_count):
                try:
                    value = self.data.get((field+'-{0}-'+inline_fields_name[idx]).format(i), '')
                except ValueError:
                    pass
                if value in temp:
                    raise forms.ValidationError(_("You have a duplicate choice in the \"%s\", you can\'t select the same choice twice")% inline_fields_display[idx] )
                else:
                    temp.append(value)      

        return self.cleaned_data
