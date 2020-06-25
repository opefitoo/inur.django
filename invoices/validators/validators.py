from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.deconstruct import deconstructible

from invoices.timesheet import SimplifiedTimesheetDetail


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

def validate_date_range_vs_timesheet(instance_id, data):
    messages = {}
    conflicts = SimplifiedTimesheetDetail.objects.filter(start_date__range=(data['start_date'], data['end_date']),
                                                         simplified_timesheet__employee__user_id=data['employee_id'])
    if 1 == conflicts.count():
        messages = {'start_date': u"Intersection avec des Temps de travail de : %s à %s" % (conflicts[0].start_date,
                                                                                            conflicts[0].end_date)}
    elif 1 < conflicts.count():
        messages = {'start_date': u"Intersection avec des Temps de travail de : %s à %s et %d autres conflits"
                                  % (conflicts[0].start_date, conflicts[0].end_date, conflicts.count() - 1)}

    return messages