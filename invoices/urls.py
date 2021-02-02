from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.views.static import serve
from rest_framework.authtoken import views as authtoken_views
from django.conf import settings
from django.urls import path

import api
from api.views import EventProcessorView
from invoices.views import delete_prestation, MedicalPrescriptionAutocomplete

admin.autodiscover()

urlpatterns = [
    # url(
    #     r'^carecode-autocomplete/$',
    #     CareCodeAutocomplete.as_view(),
    #     name='carecode-autocomplete',
    # ),
    # url(
    #     r'^patient-autocomplete/$',
    #     PatientAutocomplete.as_view(),
    #     name='patient-autocomplete',
    # ),
    url(
        r'^medical-prescription-autocomplete/$',
        MedicalPrescriptionAutocomplete.as_view(),
        name='medical-prescription-autocomplete',
    ),
    # url(
    #     r'^employee-autocomplete/$',
    #     EmployeeAutocomplete.as_view(),
    #     name='employee-autocomplete',
    # ),
    url(
        r'^admin/delete-prestation/$',
        delete_prestation,
        name='delete-prestation',
    ),
    path('admin/', admin.site.urls),
    url(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    url(r'^api-token-auth/', authtoken_views.obtain_auth_token),
    url(r'^api/v1/', include(('api.urls', 'api'), namespace='api')),
    url(
        r'^api/v1/process/(?P<numdays>\d+)/$',
        login_required(EventProcessorView.as_view()),
        name='event_processor_rest_view'),
]

urlpatterns += [
    url(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]

urlpatterns += [
    url(r'^api/v1/snippets/$', api.views.EventList.as_view()),
    url(r'^api/v1/snippets/(?P<pk>[0-9]+)/$', api.views.EventDetail.as_view())
]
# if settings.DEBUG:
#     import debug_toolbar
#     urlpatterns += [
#         url(r'^__debug__/', include(debug_toolbar.urls)),
#     ]
admin.site.site_header = "Invoice for Nurses Admin (inur)"
admin.site.site_title = "INUR Admin Portal"
admin.site.index_title = "Welcome to INUR Portal"
