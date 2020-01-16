from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible


@deconstructible
class MyRegexValidator(RegexValidator):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def __call__(self, value):
        """
        Remove spaces from value.
        """
        regex_matches = self.regex.search(str(str(value).replace(" ", "")))
        invalid_input = regex_matches if self.inverse_match else not regex_matches
        if invalid_input:
            raise ValidationError(self.message, code=self.code)
