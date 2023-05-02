from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class LongTermCareItem(models.Model):
    # code de l'acte must be unique
    code = models.CharField(max_length=10, unique=True)
    # description de l'acte
    description = models.TextField(max_length=500)
    short_description = models.CharField(max_length=50, blank=True, null=True)
    # forfait hebdomadaire en minutes  et en décimales
    weekly_package = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)

    class Meta:
        ordering = ['code']
        verbose_name = "Acte d'assurance dépendance"
        verbose_name_plural = "Actes d'assurance dépendance"

    def __str__(self):
        # if short_description is not empty
        if self.short_description:
            # code de l'acte / description de l'acte (seuelement les 10 premiers caractères)
            return "{0} / {1}".format(self.code, self.short_description)
        else:
            # code de l'acte / description de l'acte (seuelement les 10 premiers caractères)
            return "{0} / {1}".format(self.code, self.description[:10])


# class that represents a code and a dependency insurance package
class LongTermPackage(models.Model):
    code = models.CharField(max_length=10, unique=True)
    description = models.TextField(max_length=50)
    package = models.BooleanField("Forfait", default=False)
    dependence_level = models.PositiveIntegerField(blank=True, null=True,
                                                   validators=[MinValueValidator(0), MaxValueValidator(15)])
    # forfait hebdomadaire en minutes
    weekly_package = models.PositiveIntegerField(blank=True, null=True)

    def price_per_day(self, date):
        try:
            price = LongTermPackagePrice.objects.get(package=self, start_date__lte=date, end_date__gte=date)
            return price.price
        except LongTermPackagePrice.DoesNotExist:
            return None

    def price_per_year_month(self, year, month):
        try:
            price = LongTermPackagePrice.objects.get(package=self, start_date__year=year, start_date__month=month)
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

    def __str__(self):
        return "{0} / {1}".format(self.package, self.price)
