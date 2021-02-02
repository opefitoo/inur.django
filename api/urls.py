from django.conf.urls import include, url
from rest_framework import routers
from api import views

router = routers.DefaultRouter()
# router.register(r'users', views.UserViewSet)
# router.register(r'groups', views.GroupViewSet)
router.register(r'care-codes', views.CareCodeViewSet)
router.register(r'patients', views.PatientViewSet)
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
router.register(r'events-types', views.EventTypeViewSet)
# router.register(r'events', views.EventViewSet)
router.register(r'setting', views.SettingViewSet, basename='setting')


urlpatterns = [
    url(r'^', include(router.urls)),
]
