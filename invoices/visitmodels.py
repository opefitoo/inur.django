import requests
from constance import config
from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

from invoices.events import Event
from invoices.helpers.patienthelpers import list_patients_who_had_events_at_least_5_times_since_one_year
from invoices.models import Patient


# django model to store Employees Visits data got from Ios app that uses CLLocationManager


class EmployeeVisit(models.Model):
    """
    Model to store Employee Visit data
    """
    class Meta:
        verbose_name = _("Visite d'employé")
        verbose_name_plural = _("Visites d'employés")
    # user instead of employee
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Utilisateur"))
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, verbose_name=_("Patient"), blank=True, null=True)
    latitude = models.FloatField(_("Latitude"))
    longitude = models.FloatField(_("Longitude"))
    arrival_date_time = models.DateTimeField(_("Arrivée"))
    departure_date_time = models.DateTimeField(_("Départ"), blank=True, null=True)
    created_at = models.DateTimeField(_("Date de création"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Dernière mise à jour"), auto_now=True)

    def check_if_address_is_known(self, visit):
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
                            notification = f"Visit {visit.id} is a visit to patient {visit.patient}"
                            print(notification)
                            #notify_system_via_google_webhook(notification)
                        else:
                            notification = f"Visit {visit.id} is not a visit to patient {visit.patient}"
                            print(notification)
                            #notify_system_via_google_webhook(notification)
                    else:
                        print(f"Error: {data}")
            # else:
            #     # check other patients
            #     most_recent_patients = list_patients_who_had_events_at_least_5_times_since_one_year()
            #     # loop through the patients and check if the visit is a visit to one of the patients
            #     for patient in most_recent_patients:
            #         # get the patient address
            #         url = "https://api.openrouteservice.org/geocode/search"
            #         headers = {
            #             "Authorization": config.OPENROUTE_SERVICE_API_KEY,
            #             "Content-Type": "application/json",
            #         }
            #         params = {
            #             "text": patient.get_full_address(),
            #         }
            #         openrouteservice_response = requests.get(url, headers=headers, params=params)
            #         data = openrouteservice_response.json()
            #
            #         if "features" in data:
            #             patient_location = data["features"][0]["geometry"]["coordinates"]
            #             print(f"Patient {patient.id} location: {patient_location}")
            #             # calculate the distance between the patient location and the visit location
            #             base_url = "https://api.openrouteservice.org/v2/directions/driving-car"
            #             headers = {
            #                 "Authorization": config.OPENROUTE_SERVICE_API_KEY,
            #                 "Content-Type": "application/json",
            #                 "Accept": "application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8",
            #             }
            #
            #             start_coords = f"{patient_location[0]},{patient_location[1]}"
            #             end_coords = f"{visit.longitude},{visit.latitude}"
            #
            #             url = f"{base_url}?start={start_coords}&end={end_coords}"
            #             openrouteservice_response_route = requests.get(url, headers=headers, params=params)
            #             routes_data = openrouteservice_response_route.json()
            #             if "features" in routes_data:
            #                 distance = routes_data['features'][0]['properties']['summary']['distance']
            #                 print(f"Distance between patient and visit: {distance} meters")
            #                 # if the distance is less than 100 meters, then the visit is considered as a visit
            #                 # to the patient
            #                 if distance < 100:
            #                     visit.patient = patient
            #                     visit.save()
            #                     notification = f"Visit {visit.id} is a visit to patient {visit.patient}"
            #                     print(notification)
            #                     #notify_system_via_google_webhook(notification)
            #                 else:
            #                     notification = f"Visit {visit.id} is not a visit to patient {visit.patient}"
            #                     print(notification)
            #                     #notify_system_via_google_webhook(notification)
            #             else:
            #                 print(f"Error: {data}")
                # Convert the event address to GPS coordinates
        return visit.patient

    def __str__(self):
        return f"{self.user} - {self.patient} - {self.arrival_date_time}"
