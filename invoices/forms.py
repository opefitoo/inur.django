from django.forms import BaseInlineFormSet, ValidationError


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
