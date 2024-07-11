from django import forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ValidationError
from django.core.validators import EMPTY_VALUES
from django.forms import BaseInlineFormSet, ModelMultipleChoiceField, CheckboxSelectMultiple
from django.utils.translation import gettext_lazy as _

from dependence.activity import LongTermMonthlyActivityFile, LongTermMonthlyActivity
from dependence.careplan import CarePlanDetail, CareOccurrence
from dependence.detailedcareplan import MedicalCareSummaryPerPatientDetail
from dependence.enums.falldeclaration_enum import FallCircumstances, FallCognitiveMoodDiorders, FallConsequences, \
    FallIncontinences, FallRequiredMedicalActs
from dependence.falldeclaration import FallDeclaration
from dependence.longtermcareitem import LongTermCareItem


class CarePlanDetailForm(BaseInlineFormSet):
    long_term_care_items = ModelMultipleChoiceField(
        queryset=LongTermCareItem.objects.none(),
        widget=FilteredSelectMultiple(_('Codes Assurance dépendance'), True),
        required=False,
    )

    params_occurrence = ModelMultipleChoiceField(
        queryset=CareOccurrence.objects.all(),
        widget=CheckboxSelectMultiple,
        required=True,
    )
    class Meta:
        model = CarePlanDetail
        fields = '__all__'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        medical_care_summary_per_patient = self.instance.medical_care_summary_per_patient
        if medical_care_summary_per_patient:
            for form in self.forms:
                # get all LongTermCareItem for the current medical_care_summary_per_patient
                initial = MedicalCareSummaryPerPatientDetail.objects.filter(
                    medical_care_summary_per_patient=medical_care_summary_per_patient).values_list('item', flat=True)
                form.fields['long_term_care_items'].queryset = LongTermCareItem.objects.filter(pk__in=initial)
        else:
            for form in self.forms:
                form.fields['long_term_care_items'].queryset = LongTermCareItem.objects.none()

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

    def get_queryset(self):
        """
        Override the queryset to return items in the desired order.
        """
        qs = super().get_queryset()
        # Reorder queryset; assuming 'created_at' is the timestamp field for sorting
        return qs.order_by('-params_date_time')

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
            raise ValidationError(
                "Ligne %s : Valeure incorrecte pour la saturation - doit être entre 0 et 100" % rowindex)

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
                                                  required=False, )
    fall_required_medical_acts = forms.MultipleChoiceField(choices=FallRequiredMedicalActs.choices,
                                                           widget=forms.CheckboxSelectMultiple(),
                                                           required=False, )
    fall_cognitive_mood_diorders = forms.MultipleChoiceField(choices=FallCognitiveMoodDiorders.choices,
                                                             widget=forms.CheckboxSelectMultiple(),
                                                             required=False, )
    fall_incontinences = forms.MultipleChoiceField(choices=FallIncontinences.choices,
                                                   widget=forms.CheckboxSelectMultiple(),
                                                   required=False, )

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
        for field in self.declared_fields:
            if field in self.initial.keys():
                self.initial[field] = eval(self.initial[field])


class LongTermMonthlyActivityFileAdminForm(forms.ModelForm):
    class Meta:
        model = LongTermMonthlyActivityFile
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get('instance')
        if instance and instance.year and instance.month:
            self.fields['monthly_activities'].queryset = LongTermMonthlyActivity.objects.filter(year=instance.year,
                                                                                                month=instance.month)
        else:
            self.fields['monthly_activities'].queryset = LongTermMonthlyActivity.objects.none()


class LongTermCareInvoiceLineInlineFormset(forms.BaseInlineFormSet):
    def clean(self):
        super().clean()

        for form in self.forms:
            if not form.cleaned_data.get('DELETE'):
                instance = form.instance
                if not form.cleaned_data.get('skip_aev_check'):
                    instance.validate_line_are_coherent_with_medical_care_summary_per_patient()
                instance.validate_lines_are_same_period()
                instance.validate_lines_are_made_by_correct_sub_contractor()
