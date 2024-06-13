
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import viewsets

from api.mobileappserializers import MobilePatientSerializer, MobileTensionAndTemperatureParametersSerializer, \
    MobileVisitsSerializer
from dependence.models import TensionAndTemperatureParameters
from invoices.models import Patient
from invoices.visitmodels import EmployeeVisit


class MobilePatientViewSet(viewsets.ModelViewSet):
    queryset = Patient.objects.all()
    serializer_class = MobilePatientSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['name', 'code_sn', 'first_name' ]

class MobileTensionAndTemperatureParametersViewSet(viewsets.ModelViewSet):
    queryset = TensionAndTemperatureParameters.objects.all()
    serializer_class = MobileTensionAndTemperatureParametersSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['monthly_params__patient', 'monthly_params__patient__name']

    def get_queryset(self):
        """
        Optionally restricts the returned health parameters to a given time frame,
        by filtering against 'start_date' and 'end_date' query parameters in the URL.
        Order by date_time in descending order.
        """
        queryset = TensionAndTemperatureParameters.objects.all()
        start_date = self.request.query_params.get('start_date', None)
        end_date = self.request.query_params.get('end_date', None)
        if start_date is not None and end_date is not None:
            queryset = queryset.filter(params_date_time__range=[start_date, end_date])
        return queryset.order_by('-params_date_time')

class MobileVisitsViewSet(viewsets.ModelViewSet):
    queryset = EmployeeVisit.objects.all()
    serializer_class = MobileVisitsSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['user', 'patient', 'arrival_date_time', 'departure_date_time']

    def get_queryset(self):
        """
        Optionally restricts the returned visits to a given time frame,
        by filtering against 'start_date' and 'end_date' query parameters in the URL.
        Order by arrival in descending order.
        """
        queryset = EmployeeVisit.objects.all()
        start_date = self.request.query_params.get('arrival_date_time', None)
        end_date = self.request.query_params.get('departure_date_time', None)
        if start_date is not None and end_date is not None:
            queryset = queryset.filter(arrival_date_time__range=[start_date, end_date])
        return queryset.order_by('-arrival_date_time') if queryset else EmployeeVisit.objects.none()

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)  # Call the original 'create' to perform the actual creation

        # Perform your post-treatment here
        # You can access the newly created instance from the data of the response
        visit_object = EmployeeVisit.objects.get(pk=response.data['id'])

        patient = visit_object.check_if_address_is_known(visit_object)
        # add visited patient in the response
        # first json serialize patient before patient is added to the response
        if patient:
            patient_json = MobilePatientSerializer(patient).data
            response.data['patient'] = patient_json if patient else None
        return response



