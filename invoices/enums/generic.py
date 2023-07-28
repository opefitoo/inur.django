from django.db import models
from django.utils.translation import gettext_lazy as _


class CivilStatus(models.TextChoices):
    SINGLE = 'SINGLE', _('Single')
    MARRIED = 'MARRIED', _('Married')
    WIDOW = 'WIDOW', _('Widow')
    PACS = 'PACS', _('Pacs')
    DIV = 'DIV', _('Divorced')
    SEP = 'SEP', _('Separated')
    OTH = 'OTH', _('Other')


class RemoteAlarm(models.TextChoices):
    RK = 'RK', ('Roude Knap')
    SDHM = 'SDHM', ('Secher Doheem')
    HLP = 'HLP', ('Help')
    OTH = 'OTH', ('Other')


class DentalProsthesis(models.TextChoices):
    HI = 'HI', _('High')
    LO = 'LO', _('Low')
    CMPLT = 'CMPLT', _('Complete')


class DrugManagement(models.TextChoices):
    AUTNM = 'AUTNM', _('Autonomous')
    FML = 'FML', _('Family')
    NTWRK = 'NTWRK', _('Network')

class HelpForCleaning(models.TextChoices):
    FML = 'FML', _('Family')
    NTWRK = 'NTWRK', _('Network')
    TRD = 'TRD', _('Third party')


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
    TCNQ_TRD = 'TCNQ_TRD', _('Both Technical help and third party')


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


class HabitType(models.TextChoices):
    habit_morning = "MORNING", _(u"Levé")
    habit_sleep = "SLEEP", _("Coucher")
    habit_brk_fast = "BRK_FST", _(u"Petit Déjeuner")
    habit_lunch = "LNCH", _(u"Déjeuner")
    habit_dinner = "DNR", _(u"Diner")


class ActivityType(models.TextChoices):
    act_wash = "WASH", _(u"Se soigner")
    act_dress = "DRESS", _("Habillements")
    act_occupation = "OCCUP", _(u"Occupations")
    act_desires = "DSRS", _(u"Souhaits")


class SocialHabitType(models.TextChoices):
    social_family = "FML", _(u"Famille")
    social_friend = "FRND", _("Amis")
    social_important = "IMP", _(u"Personnes importantes")


class HolidayRequestChoice(models.TextChoices):
    req_morning = "MRNG", _(u"Matin")
    req_evening = "EVNG", _("Soir")
    req_full_day = "FULL", _(u"Journée entière")


class WeekDayNames(models.IntegerChoices):
    all = 0, _("Tous")
    mon = 1, _(u'Lundi')
    tue = 2, _(u'Mardi')
    wed = 3, _(u'Mercredi')
    thu = 4, _(u'Jeudi')
    fri = 5, _(u'Vendredi'),
    sat = 6, _(u'Samedi')
    sun = 7, _(u'Dimanche')


class MonthsNames(models.IntegerChoices):
    jan = 1, _("Janvier")
    feb = 2, _(u'Février')
    mar = 3, _(u'Mars')
    apr = 4, _(u'Avril')
    may = 5, _(u'Mai')
    jun = 6, _(u'Juin'),
    jul = 7, _(u'Juillet')
    aug = 8, _(u'Août')
    sep = 9, _(u'Septembre')
    oct = 10, _(u'Octobre')
    nov = 11, _(u'Novembre')
    dec = 12, _(u'Décembre')


class StoolsQty(models.IntegerChoices):
    none = 0, "-"
    little = 1, "+"
    medium = 2, "++"
    lot = 3, "+++"


class VisualAnalogueScaleLvl(models.IntegerChoices):
    none = 0, "0 (aucune douleur)"
    mild_1 = 1, "1 (simple inconfort)"
    mild = 2, "2 (simple inconfort+)"
    moderate_3 = 3, "3 (douleur légère)"
    moderate = 4, "4 (douleur légère+)"
    severe_5 = 5, "5 (douleur modérée)"
    severe = 6, "6 (douleur modérée+)"
    very_severe_7 = 7, "7 (douleur intense)"
    very_severe = 8, "8 (douleur intense+)"
    worst_pain_possible_9 = 9, "9 (douleur intolérable)"
    worst_pain_possible = 10, "10 (douleur intolérable+)"

class BatchTypeChoices(models.TextChoices):
    CNS_INF = 'CNS_INF', _('CNS Infirimier')
    CNS_INF_PACK = 'CNS_INF_PACK', _('Forfait Infirimier')
    CNS_PAL = 'CNS_PAL', _('CNS Paliatif')
    AD = 'AD', _('Assurance Dépendance')
    OTHER = 'OTHER', _('Autre')
