from constance import config
from django.db import models


class NurseCodeChoices(models.TextChoices):
    MAIN = 'MAIN', config.MAIN_NURSE_CODE
    BIS = 'BIS', config.BIS_NURSE_CODE
