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


class DependenceInsuranceLevel(models.TextChoices):
    REF = 'REF', _('Refused')
    ZRO = 'ZRO', _('0')
    ONE = 'ONE', _('1')
    TWO = 'TWO', _('2')
    TRE = 'TRE', _('3')
    FOR = 'FOR', _('4')
    FVE = 'FVE', _('5')
    SIX = 'SIX', _('6')
    SVN = 'SVN', _('7')
    EGT = 'EGT', _('8')
    NIN = 'NIN', _('9')
    TEN = 'TEN', _('10')
    ELV = 'ELV', _('11')
    TWV = 'TWV', _('12')


class NutritionAutonomyLevel(models.TextChoices):
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


class GenderType(models.TextChoices):
    gender_male = "MAL", _("Male")
    gender_female = "FEM", _("Female")
    gender_other = "OTH", _("Other")
