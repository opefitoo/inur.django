from django.conf.urls import include, url
from django.contrib import admin
from django.views.static import serve
from rest_framework.authtoken import views as authtoken_views
from django.conf import settings
from django.urls import path

from invoices.views import CareCodeAutocomplete, PatientAutocomplete, EmployeeAutocomplete, \
    MedicalPrescriptionAutocomplete, delete_prestation

urlpatterns = [
    url(
        r'^carecode-autocomplete/$',
        CareCodeAutocomplete.as_view(),
        name='carecode-autocomplete',
    ),
    url(
        r'^patient-autocomplete/$',
        PatientAutocomplete.as_view(),
        name='patient-autocomplete',
    ),
    url(
        r'^medical-prescription-autocomplete/$',
        MedicalPrescriptionAutocomplete.as_view(),
        name='medical-prescription-autocomplete',
    ),
    url(
        r'^employee-autocomplete/$',
        EmployeeAutocomplete.as_view(),
        name='employee-autocomplete',
    ),
    url(
        r'^admin/delete-prestation/$',  
        delete_prestation,
        name='delete-prestation',
    ),
    path('admin/', admin.site.urls),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth/', authtoken_views.obtain_auth_token),
    url(r'^api/v1/', include(('api.urls', 'api'), namespace='api'))
]

urlpatterns += [
    url(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]
# if settings.DEBUG:
#     import debug_toolbar
#     urlpatterns += [
#         url(r'^__debug__/', include(debug_toolbar.urls)),
#     ]