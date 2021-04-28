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
