from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.mobileappviews import MobilePatientViewSet, MobileTensionAndTemperatureParametersViewSet, MobileVisitsViewSet

router = DefaultRouter()
router.register(r'm-patients', MobilePatientViewSet)
router.register(r'm-health-params', MobileTensionAndTemperatureParametersViewSet)
router.register(r'm-visits', MobileVisitsViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
