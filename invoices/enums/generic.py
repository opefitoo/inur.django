from django.db import models
from django.utils.translation import gettext_lazy as _


class CivilStatus(models.TextChoices):
    SINGLE = 'SINGLE', _('Single')
    MARRIED = 'MARRIED', _('Married')
    WIDOW = 'WIDOW', _('Widow')
    PACS = 'PACS', _('Pacs')


class RemoteAlarm(models.TextChoices):
    RK = 'RK', ('Roude Knap')
    SDHM = 'SDHM', ('Secher Doheem')
    HLP = 'HLP', ('Help')


class DentalProsthesis(models.TextChoices):
    HI = 'HI', _('High')
    LO = 'LO', _('Low')
    CMPLT = 'CMPLT', _('Complete')


class DrugManagement(models.TextChoices):
    AUTNM = 'AUTNM', _('Autonomous')
    FML = 'FML', _('Family')
    NTWRK = 'NTWRK', _('Network')


class NutrionAutonomyLevel(models.TextChoices):
    AUTNM = 'AUTNM', _('Autonomous')
    FML = 'FML', _('Family')
    NTWRK = 'NTWRK', _('Network')
    TB = 'TB', _('Tube')


class MobilizationsType(models.TextChoices):
    AUTNM = 'AUTNM', _('Autonomous')
    TCNQ = 'TCNQ', _('With technical help')
    TRD = 'TRD', _('With third party')
    BD = 'BD', _('Bedridden')


class HearingAid(models.TextChoices):
    HI = 'RIT', _('Right')
    LO = 'LFT', _('Left')
    BTH = 'BTH', _('Both')


class HouseType(models.TextChoices):
    FLAT = 'FLAT', _('Flat')
    HOUSE = 'HOUSE', _('House')
