from django.urls import include, re_path
from django.urls import path
from rest_framework import routers
from rest_framework.authtoken.views import obtain_auth_token

from api import views, cnsstatsviews
from api.clockinview import simplified_timesheet_clock_in_view, simplified_timesheet_clock_out_view
from api.converterview import MT940toOFXConverterView
from api.views import LockCarView, UnlockCarView, car_location, is_car_locked, can_user_lock_car, CarBookingListView

router = routers.DefaultRouter()
# router.register(r'users', views.UserViewSet)
router.register(r'employees-avatars', views.EmployeeAvatarSerializerViewSet)
router.register(r'employees', views.EmployeeViewSet)
router.register(r'shy-employees', views.ShyEmployeesViewSet, basename='shy-employees')
router.register(r'shifts', views.ShiftViewSet)
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
router.register(r'sub-contractors', views.SubContractorViewSet)
router.register(r'simplified-timesheets', views.SimplifiedTimesheetViewSet)
router.register(r'cars', views.CarViewSet)

# router.register(r'events', views.EventViewSet)

urlpatterns = [
    re_path(r'^', include(router.urls)),
]

urlpatterns += [
    path('convert/', MT940toOFXConverterView.as_view(), name='convert-mt940-to-ofx'),
]

urlpatterns += [
    path('how_many_employees_with_specific_cct_sas_grade/',
         cnsstatsviews.how_many_employees_with_specific_cct_sas_grade,
         name='how-many-employees-with-specific-cct-sas-grade'),
]

urlpatterns += [
    path('v1/lock_car/<int:pk>/', LockCarView.as_view(), name='lock_car'),
    path('v1/unlock_car/<int:pk>/', UnlockCarView.as_view(), name='unlock_car'),
    #path('v1/cars/', views.CarListView.as_view(), name='car_list'),
    path('v1/car_location/<int:car_id>/', car_location, name='car_location'),
    path('v1/is_car_locked/<int:car_id>/', is_car_locked, name='is_car_locked'),
    path('v1/can_user_lock_car/<int:car_id>/', can_user_lock_car, name='can_user_lock_car'),
    path('v1/car_bookings/', CarBookingListView.as_view(), name='car_booking_list'),
]

urlpatterns += [
    path('v1/auth-token/', obtain_auth_token, name='api-token'),
]

urlpatterns += [
    path('v1/simplified_timesheet_clock_in/', simplified_timesheet_clock_in_view, name='simplified_timesheet_clock_in'),
    path('v1/simplified_timesheet_clock_out/', simplified_timesheet_clock_out_view, name='simplified_timesheet_clock_out'),
]
