from django.db import models

from invoices.models import Patient


class DistanceMatrix(models.Model):
    """
    DistanceMatrix model to store the distance and duration between two locations
    data is fetched from Google Distance Matrix API.
    """
    patient_origin = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient_origin_distance_matrix')
    patient_destination = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='patient_destination_distance_matrix')
    distance_in_km = models.PositiveSmallIntegerField()
    duration_in_mn = models.PositiveSmallIntegerField()
    # technical fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Distance from {self.patient_origin} to {self.patient_destination} is {self.distance_in_km} km and it takes {self.duration_in_mn} mn"

    class Meta:
        verbose_name_plural = "Distances Matrix"
        verbose_name = "Distance Matrix"
        ordering = ['patient_origin', 'patient_destination']
        unique_together = ['patient_origin', 'patient_destination']
