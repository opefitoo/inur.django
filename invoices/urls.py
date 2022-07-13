from django.urls import include, re_path
from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView
from django.views.static import serve
from rest_framework.authtoken import views as authtoken_views
from django.conf import settings

import api
from api.views import EventProcessorView, cleanup_event, whois_off, whois_available, get_bank_holidays, \
    get_active_care_plans
from invoices import views
from invoices.eventviews import Calendar1View, load_calendar_form, update_calendar_form
from invoices.views import delete_prestation

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
    # url(
    #     r'^medical-prescription-autocomplete/$',
    #     MedicalPrescriptionAutocomplete.as_view(),
    #     name='medical-prescription-autocomplete',
    # ),
    # url(
    #     r'^employee-autocomplete/$',
    #     EmployeeAutocomplete.as_view(),
    #     name='employee-autocomplete',
    # ),

    re_path(
        '^admin/delete-prestation/$',
        delete_prestation,
        name='delete-prestation',
    ),
    re_path(
        r'^api/v1/cleanup_event/$',
        cleanup_event,
        name='cleanup_event',
    ),
    re_path(
        r'^api/v1/whois_off/$',
        whois_off,
        name='whois_off',
    ),
    re_path(
        r'^api/v1/whois_available/$',
        whois_available,
        name='whois_available',
    ),
    re_path(
        r'^api/v1/get_bank_holidays/$',
        get_bank_holidays,
        name='get_bank_holidays',
    ),
    re_path(
        r'^api/v1/get_active_care_plans/$',
        get_active_care_plans,
        name='get_active_care_plans',
    ),
    re_path('admin/', admin.site.urls),
    re_path(r'^api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    re_path(r'^api-token-auth/', authtoken_views.obtain_auth_token),
    re_path(r'^api/v1/', include(('api.urls', 'api'), namespace='api')),
    re_path(
        r'^api/v1/process/(?P<numdays>\d+)/$',
        login_required(EventProcessorView.as_view()),
        name='event_processor_rest_view'),

]

urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {
        'document_root': settings.MEDIA_ROOT,
    }),
]

urlpatterns += [
    # re_path('', Calendar1View.as_view(), name='calendar_1'),
    re_path('^admin/EventWeekList/update-event/<int:id>/', Calendar1View.as_view(),
            name='update-even'),
    re_path('^admin/EventWeekList/add-event-form/', load_calendar_form, name='load-calendar-form'),
    re_path('update-event-form/',
            update_calendar_form,
            name='update-calendar-form'),
]

urlpatterns += [
    re_path(r'^api/v1/event_list/$', api.views.EventList.as_view()),
    re_path(r'^api/v1/event_list/(?P<pk>[0-9]+)/$', api.views.EventDetail.as_view()),
]
urlpatterns += [
    re_path(r'^favicon\.ico$', RedirectView.as_view(url='/static/images/favicon.ico')),
]
urlpatterns += [
    # … other patterns
    re_path("select2/", include("django_select2.urls")),
    # … other patterns
]
# if settings.DEBUG:
#     import debug_toolbar
#
#     urlpatterns += [
#         path('__debug__/', include(debug_toolbar.urls)),
#     ]
admin.site.site_header = "Invoice for Nurses Admin (inur)"
admin.site.site_title = "INUR Admin Portal"
admin.site.index_title = "Welcome to INUR Portal"
