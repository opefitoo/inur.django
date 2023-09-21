from django.db import models
from django.utils.translation import gettext_lazy as _


class BedsoreEvolutionStatus(models.TextChoices):
    NA = 'NA', _('Première visite')
    BETTER = 'BETTER', _('Amélioration')
    STABLE = 'STABLE', _('Stable')
    WORSE = 'WORSE', _('Dégradation')
