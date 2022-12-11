from django.db import models
from django.utils.translation import gettext_lazy as _


class FallCircumstances(models.TextChoices):
    FCI_ON_SAME_LEVEL = "FCI_ON_SAME_LEVEL", _(
        "Chute de plain-pied résultant de glissade, faux-pas et trébuchement"
    )
    FCI_FROM_BED = "FCI_FROM_BED", _("Chute d’un lit")
    FCI_FROM_CHAIR = "FCI_FROM_CHAIR", _("Chute d’une chaise")
    FCI_FROM_STAIRS = "FCI_FROM_STAIRS", _("Chute dans un escalier et de marches")
    FCI_WHILE_HELD = "FCI_WHILE_HELD", _("Chute en étant porté ou soutenu par un tiers")
    FCI_FROM_WHEELC = "FCI_FROM_WHEELC", _("Chute d’un fauteuil roulant")
    FCI_FROM_TOILET = "FCI_FROM_TOILET", _("Chute d’un siège de toilette")
    FCI_OTHER_CAUSES = "FCI_OTHER_CAUSES", _("Autre")


class FallConsequences(models.TextChoices):
    FCO_NO_TRAUMA = "FCO_NO_TRAUMA", _("Indemne de lésions traumatiques")
    FCO_SUPERF_TRAUMA = "FCO_SUPERF_TRAUMA", _(
        "Lésion(s) traumatique(s) superficielle(s) (abrasion, contusion, ecchymose, hématome)"
    )
    FCO_OPEN_WOUND = "FCO_OPEN_WOUND", _("Plaie(s) ouverte(s) (coupure, lacération)")
    FCO_DISLOCATION = "FCO_DISLOCATION", _("Luxation, entorse, foulure")
    FCO_PAIN = "FCO_PAIN", _("Douleurs (évaluer la douleur svp)")
    FCO_OTHER_CAUSES = "FCO_OTHER_CAUSES", _("Autre")


class FallRequiredMedicalActs(models.TextChoices):
    FRMA_RADIO = "FRMA_RADIO", _("Investigation radiologique")
    FRMA_MINOR_SURGERY = "FRMA_MINOR_SURGERY", _("Petite chirurgie")
    FRMA_TRANSFER = "FRMA_TRANSFER", _("Transfert")
    FRMA_NURS_SUPERV = "FRMA_NURS_SUPERV", _("Surveillance infirmière accrue")
    FRMA_RESTRAINT = "FRMA_RESTRAINT", _("Contention")
    FRMA_OTHER_CAUSES = "FCO_OTHER_CAUSES", _("Autres mesures")

class FallMedicationsRiskFactors(models.TextChoices):
    FMRF_MEDS = "FMRF_MEDS", _("Médicaments (psychotropes, anti-hypertenseurs, polypragmasie etc.)")
    FMRF_OTHER = "FMRF_OTHER", _("Autres: > 4 médicaments")

class FallCognitiveMoodDiorders(models.TextChoices):
    FCMD_DROWSINESS_ETC = "FCMD_DROWSINESS_ETC", _("Somnolence, stupeur ou coma")
    FCMD_DESORIENT = "FCMD_DESORIENT", _("Désorientation, confusion")
    FCMD_AGET = "FCMD_AGET", _("Agitation")
    FCMD_OTHER = "FCMD_OTHER", _("Autres altérations des fonctions cognitives")

class FallIncontinences(models.TextChoices):
    FI_URINARY = "FCMD_URINARY", _("Incontinence urinaire (non sondé)")
    FI_FECAL = "FI_FECAL", _("Incontinence des matières fécales")

class FallmMbilityDisability(models.TextChoices):
    FMD_NONE = "FCMD_NONE", _("Se déplace seul, sans difficultés, sans moyens auxiliaires")
    FMD_DIFFICULTY = "FMD_DIFFICULTY", _("Se déplace seul avec difficulté avec ou sans moyens auxiliaires")
    FMD_ACCOMPANIED = "FMD_ACCOMPANIED", _("Se déplace accompagné sans moyens auxiliaires")
    FMD_AUXILIARY = "FMD_AUXILIARY", _("Se déplace accompagné avec moyens auxiliaires")
