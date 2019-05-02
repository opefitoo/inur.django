"""invoices URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""

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
    url(r'^jet/', include('jet.urls', 'jet')),
    #url(r'^jet/dashboard/', include('jet.dashboard.urls', 'jet-dashboard')),
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