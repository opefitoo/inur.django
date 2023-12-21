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

class UnavailabilityTypeChoices(models.TextChoices):
    # < xs: enumeration
    # value = "DEBUT" / >
    # < xs: enumeration
    # value = "RETOUR" / >
    # < xs: enumeration
    # value = "CORRECTION" / >
    # < xs: enumeration
    # value = "DEFINITIVE" / >
    DEBUT = "DEBUT", _("Start")
    RETOUR = "RETOUR", _("Return")
    CORRECTION = "CORRECTION", _("Correction")
    DEFINITIVE = "DEFINITIVE", _("Definitive")
