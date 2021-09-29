from django.core.exceptions import ValidationError
from django.forms import BaseInlineFormSet


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
