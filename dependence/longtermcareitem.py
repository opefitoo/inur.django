from django.db import models


class LongTermCareItem(models.Model):
    # code de l'acte must be unique
    code = models.CharField(max_length=10, unique=True)
    # description de l'acte
    description = models.TextField(max_length=500)
    class Meta:
        ordering = ['code']
        verbose_name = "Acte d'assurance dépendance"
        verbose_name_plural = "Actes d'assurance dépendance"
    def __str__(self):
        return f"{self.code} - {self.description}"
