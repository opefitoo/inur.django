from django.db import models
from django.utils.translation import gettext_lazy as _


class FallCircumstances(models.TextChoices):
    FCI_ON_SAME_LEVEL = "FCI_ON_SAME_LEVEL", _(
        "Fall on the same level as a result of slipping, stumbling and tripping"
    )
    FCI_FROM_BED = "FCI_FROM_BED", _("Fall from a bed")
    FCI_FROM_CHAIR = "FCI_FROM_CHAIR", _("Fall from a chair")
    FCI_FROM_STAIRS = "FCI_FROM_STAIRS", _("Fall down stairs and steps")
    FCI_WHILE_HELD = "FCI_WHILE_HELD", _("Fall while being carried or supported by a third party")
    FCI_FROM_WHEELC = "FCI_FROM_WHEELC", _("Fall from a wheelchair")
    FCI_FROM_TOILET = "FCI_FROM_TOILET", _("Fall from a toilet seat")
    FCI_OTHER_CAUSES = "FCI_OTHER_CAUSES", _("Other")


class FallConsequences(models.TextChoices):
    FCO_NO_TRAUMA = "FCO_NO_TRAUMA", _("Free from traumatic injuries")
    FCO_SUPERF_TRAUMA = "FCO_SUPERF_TRAUMA", _(
        "Superficial traumatic lesion(s) (abrasion, contusion, bruise, hematoma)"
    )
    FCO_OPEN_WOUND = "FCO_OPEN_WOUND", _("Open wound(s) (cut, laceration)")
    FCO_DISLOCATION = "FCO_DISLOCATION", _("Dislocation, sprain, strain")
    FCO_PAIN = "FCO_PAIN", _("Pain (please assess pain)")



class FallRequiredMedicalActs(models.TextChoices):
    FRMA_RADIO = "FRMA_RADIO", _("Radiological investigation")
    FRMA_MINOR_SURGERY = "FRMA_MINOR_SURGERY", _("Minor surgery")
    FRMA_TRANSFER = "FRMA_TRANSFER", _("Transfer")
    FRMA_NURS_SUPERV = "FRMA_NURS_SUPERV", _("Increased nursing supervision")
    FRMA_RESTRAINT = "FRMA_RESTRAINT", _("Restraint")

class FallMedicationsRiskFactors(models.TextChoices):
    FMRF_MEDS = "FMRF_MEDS", _("Medicines (psychotropics, anti-hypertensives, polypragmasia etc.)")
    FMRF_OTHER = "FMRF_OTHER", _("Others: > 4 drugs")

class FallCognitiveMoodDiorders(models.TextChoices):
    FCMD_DROWSINESS_ETC = "FCMD_DROWSINESS_ETC", _("Drowsiness, stupor or coma")
    FCMD_DESORIENT = "FCMD_DESORIENT", _("Disorientation, confusion")
    FCMD_AGET = "FCMD_AGET", _("Agitation")
    FCMD_OTHER = "FCMD_OTHER", _("Other impairments of cognitive functions")

class FallIncontinences(models.TextChoices):
    FI_URINARY = "FCMD_URINARY", _("Urinary incontinence (not catheterized)")
    FI_FECAL = "FI_FECAL", _("Incontinence of feces")

class FallmMbilityDisability(models.TextChoices):
    FMD_NONE = "FCMD_NONE", _("Moves alone, without difficulty, without auxiliary means")
    FMD_DIFFICULTY = "FMD_DIFFICULTY", _("Moves independently with difficulty with or without aids")
    FMD_ACCOMPANIED = "FMD_ACCOMPANIED", _("Moves accompanied without auxiliary means")
    FMD_AUXILIARY = "FMD_AUXILIARY", _("Moves accompanied with auxiliary means")
