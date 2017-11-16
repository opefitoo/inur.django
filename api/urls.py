from django.conf.urls import include, url
from rest_framework import routers
from api import views


router = routers.DefaultRouter()
router.register(r'users', views.UserViewSet)
router.register(r'groups', views.GroupViewSet)
router.register(r'care-codes', views.CareCodeViewSet)
router.register(r'patients', views.PatientViewSet)
router.register(r'prestations', views.PrestationViewSet)
router.register(r'invoice-items', views.InvoiceItemViewSet)
router.register(r'private-invoice-items', views.PrivateInvoiceItemViewSet)

urlpatterns = [
    url(r'^', include(router.urls)),
]
