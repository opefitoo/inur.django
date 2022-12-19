from django.db import models
from django.utils.translation import gettext_lazy as _


class HolidayRequestWorkflowStatus(models.TextChoices):
    PENDING = 'PNDG', _('Pending')
    REFUSED = 'REF', _('Refused')
    ACCEPTED = 'OK', _('Accepted')


class ContractType(models.TextChoices):
    CDD = "CDD", _("CDD")
    CDI = "CDI", _("CDI")
    STG = "STG", _("Stage")
