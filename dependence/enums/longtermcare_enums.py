from django.db import models
from django.utils.translation import gettext_lazy as _

class ChangeTypeChoices(models.TextChoices):
    # < xs: enumeration
    # value = "ENTREE" / >
    # < xs: enumeration
    # value = "SORTIE" / >
    # < xs: enumeration
    # value = "CORRECTION" / >
    ENTRY = "ENTRY", _("Entry")
    EXIT = "EXIT", _("Exit")
    CORRECTION = "CORRECTION", _("Correction")
