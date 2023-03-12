from invoices.models import Patient


def get_patient_by_id(patient_id):
    return Patient.objects.get(id=patient_id)
