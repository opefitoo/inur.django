from django.db import models
from django.utils.translation import gettext_lazy as _

class AlertLevels(models.TextChoices):
    INFO = 'INFO', _('Info')
    WARNING = 'WARNING', _('Warning')
    DANGER = 'DANGER', _('Danger')
