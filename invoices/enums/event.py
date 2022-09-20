from django.db import models
from django.utils.translation import gettext_lazy as _


class EventTypeEnum(models.TextChoices):
    BIRTHDAY = 'BIRTHDAY', _('Birthday')
    CARE = 'CARE', _('Soin')
    ASS_DEP = 'ASS_DEP', _('Soin Assurance dépendance')
    GENERIC = 'GENERIC', _('Général pour Patient (non soin)')
    GNRC_EMPL = 'GNRC_EMPL', _('Général pour Employé')

