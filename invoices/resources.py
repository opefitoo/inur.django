from django.db import models


class Car(models.Model):
    class Meta:
        ordering = ['-name']

    name = models.CharField(max_length=20)
    licence_plate = models.CharField(max_length=8)

    def __str__(self):
        return '%s - %s' % (self.name, self.licence_plate)


class ExpenseCard(models.Model):
    class Meta:
        ordering = ['-name']

    name = models.CharField(max_length=20)
    number = models.CharField(max_length=20, default="XX1111")
    pin = models.CharField(max_length=4, default="1111")
    car_link = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return 'Card: %s - %s' % (self.name, self.number)
