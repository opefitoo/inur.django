from datetime import date

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q


class LongTermCareItem(models.Model):
    # code de l'acte must be unique
    code = models.CharField(max_length=10, unique=True)
    # description de l'acte
    description = models.TextField(max_length=500, blank=True, null=True)
    short_description = models.CharField(max_length=60, blank=True, null=True)
    # forfait hebdomadaire en minutes  et en décimales
    weekly_package = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)

    class Meta:
        ordering = ['code']
        verbose_name = "Relevé type des aides et soins"
        verbose_name_plural = "Relevés type des aides et soins"

    def __str__(self):
        return self.code
        # if short_description is not empty
        # if self.short_description:
        #     # code de l'acte / description de l'acte (seuelement les 10 premiers caractères)
        #     return "{0} / {1}".format(self.code, self.short_description)
        # else:
        #     # code de l'acte / description de l'acte (seuelement les 10 premiers caractères)
        #     return "{0} / {1}".format(self.code, self.description[:10])


# class that represents a code and a dependency insurance package
class LongTermPackage(models.Model):
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(max_length=50)
    package = models.BooleanField("Forfait", default=False)
    dependence_level = models.PositiveIntegerField(blank=True, null=True,
                                                   validators=[MinValueValidator(0), MaxValueValidator(780)])
    # forfait hebdomadaire en minutes
    weekly_package = models.PositiveIntegerField(blank=True, null=True)

    def price_per_day(self, date):
        try:
            price = LongTermPackagePrice.objects.get(package=self, start_date__lte=date, end_date__gte=date)
            return price.price
        except LongTermPackagePrice.DoesNotExist:
            return None
    def get_latest_price_and_date(self):
        try:
            price = LongTermPackagePrice.objects.filter(package=self).latest('start_date')
            return price
        except LongTermPackagePrice.DoesNotExist:
            return None


    def price_per_year_month(self, year, month):
        try:
            target_date = date(year, month, 1)
            price = LongTermPackagePrice.objects.get(
                Q(package=self),
                Q(start_date__lte=target_date),
                Q(Q(end_date__gte=target_date) | Q(end_date__isnull=True))
            )
            return price.price
        except LongTermPackagePrice.DoesNotExist:
            return None

    class Meta:
        ordering = ['code']
        verbose_name = "Acte assurance dépendance"
        verbose_name_plural = "Acte assurance dépendance"

    def __str__(self):
        return "{0} / {1}".format(self.code, self.description)


class LongTermPackagePrice(models.Model):
    package = models.ForeignKey(LongTermPackage, on_delete=models.CASCADE, related_name='price_validity_package')
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    price = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        ordering = ['package']
        verbose_name = "Prix assurance dépendance"
        verbose_name_plural = "Prix assurance dépendance"
        constraints = [
            models.UniqueConstraint(fields=['package', 'start_date'],
                                    name='unique package price')
        ]

    def __str__(self):
        return "{0} / {1} - {2}".format(self.start_date, self.package, self.price)
