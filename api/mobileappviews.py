import requests
from constance import config
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters
from rest_framework import viewsets

from api.mobileappserializers import MobilePatientSerializer, MobileTensionAndTemperatureParametersSerializer, \
    MobileVisitsSerializer
from dependence.models import TensionAndTemperatureParameters
from invoices.events import Event
from invoices.models import Patient
from invoices.notifications import notify_system_via_google_webhook
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
        visit = EmployeeVisit.objects.get(pk=response.data['id'])

        # check if the visit has a departure date then checks on the employee's planning which patient was visited
        if visit.departure_date_time:
            # get the Event object that corresponds to the visit
            # filter event that are more or less at the same time
            events = Event.objects.filter(day=visit.arrival_date_time.date(),
                                          employees__user=visit.user)
            if events:
                # Convert the event address to GPS coordinates
                url = "https://api.openrouteservice.org/geocode/search"
                headers = {
                    "Authorization": config.OPENROUTE_SERVICE_API_KEY,
                    "Content-Type": "application/json",
                }
                params = {
                    "text": events[0].get_event_address(),
                }
                openrouteservice_response = requests.get(url, headers=headers, params=params)
                data = openrouteservice_response.json()

                if "features" in data:
                    event_location = data["features"][0]["geometry"]["coordinates"]
                    print(f"Event {events[0].id} location: {event_location}")
                    # calculate the distance between the event location and the visit location
                    base_url = "https://api.openrouteservice.org/v2/directions/driving-car"
                    headers = {
                        "Authorization": config.OPENROUTE_SERVICE_API_KEY,
                        "Content-Type": "application/json",
                        "Accept": "application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8",
                    }

                    start_coords = f"{event_location[0]},{event_location[1]}"
                    end_coords = f"{visit.longitude},{visit.latitude}"

                    url = f"{base_url}?start={start_coords}&end={end_coords}"
                    openrouteservice_response_route = requests.get(url, headers=headers, params=params)
                    routes_data = openrouteservice_response_route.json()
                    if "features" in routes_data:
                        distance = routes_data['features'][0]['properties']['summary']['distance']
                        print(f"Distance between event and visit: {distance} meters")
                        # if the distance is less than 100 meters, then the visit is considered as a visit
                        # to the patient
                        if distance < 100:
                            visit.patient = events[0].patient
                            visit.save()
                            notification = f"Visit {visit.user} is a visit to patient {visit.patient}"
                            print(notification)
                            notify_system_via_google_webhook(notification)
                        else:
                            notification = f"Visit {visit.user} is not a visit to patient {visit.patient}"
                            print(notification)
                            notify_system_via_google_webhook(notification)
                    else:
                        print(f"Error: {data}")
        # add visited patient in the response
        # first json serialize patient before patient is added to the response
        patient_json = MobilePatientSerializer(visit.patient).data
        response.data['patient'] = patient_json if visit.patient else None
        return response



