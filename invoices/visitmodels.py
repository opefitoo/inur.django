

# django model to store Employees Visits data got from Ios app that uses CLLocationManager

from django.db import models
from django.utils.translation import gettext_lazy as _

from invoices.employee import Employee
from invoices.models import Patient


class EmployeeVisit(models.Model):
    """
    Model to store Employee Visit data
    """
    class Meta:
        verbose_name = _("Visite d'employé")
        verbose_name_plural = _("Visites d'employés")

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_("Employé"))
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, verbose_name=_("Patient"), blank=True, null=True)
    latitude = models.FloatField(_("Latitude"))
    longitude = models.FloatField(_("Longitude"))
    arrival_date_time = models.DateTimeField(_("Arrivée"))
    departure_date_time = models.DateTimeField(_("Départ"), blank=True, null=True)

    def __str__(self):
        return f"{self.employee} - {self.patient} - {self.timestamp}"
