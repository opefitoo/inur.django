from django.db import models


class Car(models.Model):
    class Meta:
        ordering = ['-name']
    name = models.CharField(max_length=20)
    licence_plate = models.CharField(max_length=8)


class ExpenseCard(models.Model):
    class Meta:
        ordering = ['-name']
    name = models.CharField(max_length=20)
    photo = models.ImageField()
    car_link = models.ForeignKey(Car, on_delete=models.SET_NULL)