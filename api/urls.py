from django.urls import include, re_path
from django.urls import path
from rest_framework import routers

from api import views, cnsstatsviews
from api.converterview import MT940toOFXConverterView

router = routers.DefaultRouter()
# router.register(r'users', views.UserViewSet)
router.register(r'employees-avatars', views.EmployeeAvatarSerializerViewSet)
# router.register(r'groups', views.GroupViewSet)
router.register(r'care-codes', views.CareCodeViewSet)
router.register(r'patients', views.PatientViewSet)
router.register(r'dependant-patients', views.DependantPatientViewSet)
router.register(r'physicians', views.PhysicianViewSet)
router.register(r'prestations', views.PrestationViewSet)
router.register(r'invoice-items', views.InvoiceItemViewSet)
router.register(r'job-positions', views.JobPositionViewSet)
router.register(r'batch', views.BatchViewSet)
router.register(r'timesheets', views.TimesheetViewSet)
router.register(r'timesheet-tasks', views.TimesheetTaskViewSet)
router.register(r'medical-prescriptions', views.MedicalPrescriptionViewSet)
router.register(r'hospitalizations', views.HospitalizationViewSet)
router.register(r'validity-dates', views.ValidityDateViewSet)
router.register(r'patient-anamnesis', views.PatientAnamnesisViewSet)
router.register(r'events-types', views.EventTypeViewSet)
router.register(r'employee', views.EmployeeSerializerViewSet)
router.register(r'caregivers', views.EmployeeSerializerViewSet)
router.register(r'longtermcare-activity', views.LongTermMonthlyActivityViewSet)
router.register(r'employee-contract-detail', views.EmployeeContractDetailSerializerViewSet)
router.register(r'distance-matrix', views.DistanceMatrixSerializerViewSet)
router.register(r'shifts', views.ShiftViewSet)
router.register(r'employee_shifts', views.EmployeeShiftViewSet)


# router.register(r'events', views.EventViewSet)

urlpatterns = [
    re_path(r'^', include(router.urls)),
]

urlpatterns += [
    path('convert/', MT940toOFXConverterView.as_view(), name='convert-mt940-to-ofx'),
]

urlpatterns += [
    path('how_many_employees_with_specific_cct_sas_grade/', cnsstatsviews.how_many_employees_with_specific_cct_sas_grade,
         name='how-many-employees-with-specific-cct-sas-grade'),
]
