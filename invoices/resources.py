import json
import os
from datetime import datetime
from typing import List

import pytz
import requests
from constance import config
from django.core.cache import cache
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from oauthlib.oauth2 import LegacyApplicationClient, TokenExpiredError
from requests_oauthlib import OAuth2Session
from vininfo import Vin

from invoices.actions.helpers import invoxia_position_and_battery


def get_last_token():
    if len(ConvadisOAuth2Token.objects.all()) > 0:
        return ConvadisOAuth2Token.objects.first().token
    return None


def token_saver(token):
    ConvadisOAuth2Token.objects.all().delete()
    ConvadisOAuth2Token(token=token).save()


def get_oauth2_convadis_rest_client_v2(refresh_token=False):
    if not refresh_token:
        token = get_last_token()
        if token:
            # check if token is expired knowing that oken['expires_at'] is of type float
            if token['expires_at'] < datetime.now().timestamp():
                # print formatted date
                print("token expired at: %s" % datetime.fromtimestamp(token['expires_at']))
                token = None
            return OAuth2Session('SUR.lu', token=token)
        else:
            return None
    else:
        oauth_session = OAuth2Session(client=LegacyApplicationClient(client_id=config.CONVADIS_CLIENT_ID))
        token = oauth_session.fetch_token(
            token_url=config.CONVADIS_URL,
            username='username',
            password='password',
            client_id=config.CONVADIS_CLIENT_ID,
            client_secret=config.CONVADIS_SECRET_ID)
        client = OAuth2Session(config.CONVADIS_CLIENT_ID, token=token)
        token_saver(token)
        return client


class ConvadisOAuth2Token(models.Model):
    token = models.JSONField()


def find_vehicle_position(convadis_identifier, vehicles_last_position):
    print("*** convadis_identifier: {} and vehicles last position in cache is {}".format(convadis_identifier,
                                                                                     vehicles_last_position))
    for vehicle_last_position in vehicles_last_position:
        try:
            vehicle_id = vehicle_last_position.get('vehicleId')
            if isinstance(vehicle_id, int) and vehicle_id == int(convadis_identifier):
                return (
                    vehicle_last_position.get('timestamp', 'n/a'),
                    vehicle_last_position.get('lat', 'n/a'),
                    vehicle_last_position.get('lon', 'n/a')
                )
        except ValueError:
            raise ValueError("error: vehicleId is not an integer %s - %s" %  (vehicle_last_position, vehicles_last_position))
        except AttributeError:
            raise AttributeError("error: vehicleId is not an integer %s - %s" % (vehicle_last_position, vehicles_last_position))
    return "n/a"

def vehicle_speed(convadis_identifier, speed):
    if 'code' in speed:
        return "Error: %s" % speed['message']
    for speed in speed:
        if speed['vehicleId'] == int(convadis_identifier):
            return speed['sog']


def vehicle_mileage(convadis_identifier, mil):
    for mil in mil:
        if mil["vehicleId"] == int(convadis_identifier):
            return mil["totalMileage"]["value"]


def registration_card_storage_location(instance, filename):
    file_name, file_extension = os.path.splitext(filename)
    path = os.path.join("Doc. Resources", "%s" % instance.licence_plate)
    filename = '%s_%s_%s_%s%s' % (
        instance.licence_plate, timezone.now().date().strftime('%Y'), timezone.now().date().strftime('%b'),
        "carte_grise", file_extension)
    return os.path.join(path, filename)


def maintenance_file_storage_location(instance, filename):
    file_name, file_extension = os.path.splitext(filename)
    path = os.path.join("Doc. Resources", "%s" % instance.car_link.licence_plate)
    filename = '%s_%s_%s_%s%s' % (
        instance.car_link.licence_plate, timezone.now().date().strftime('%Y'), timezone.now().date().strftime('%b'),
        "maintenance", file_extension)
    return os.path.join(path, filename)


class Car(models.Model):
    class Meta:
        ordering = ['-name']
        verbose_name = u"Voiture, Clé ou coffre"
        verbose_name_plural = u"Voitures, Clés ou coffres"

    name = models.CharField(max_length=20)
    licence_plate = models.CharField(max_length=8)
    is_connected_to_convadis = models.BooleanField(default=False)
    invoxia_identifier = models.CharField(max_length=20, default=None, blank=True, null=True)
    convadis_identifier = models.CharField(max_length=20, default=None, blank=True, null=True)
    registration_card = models.FileField(upload_to=registration_card_storage_location,
                                         help_text=_("You can attach the scan of the registration card of the car"),
                                         null=True, blank=True)
    vin_number = models.CharField(max_length=20, default=None, blank=True, null=True)

    @property
    def battery_or_fuel_level(self):
        if self.invoxia_identifier:
            battery_level = invoxia_position_and_battery(self.invoxia_identifier)[1]
            if battery_level:
                return battery_level
            else:
                return "n/a"

    @property
    def geo_localisation_of_car(self):
        # if not self.is_connected_to_convadis:
        #     return "n/a"
        # if self.is_connected_to_convadis and not self.convadis_identifier:
        #     return "n/a Error: convadis id is not set"
        if not self.is_connected_to_convadis and not self.invoxia_identifier:
            return "n/a"
        if self.is_connected_to_convadis:
            if not self.convadis_identifier:
                return "n/a Error: convadis id is not set"
        elif self.invoxia_identifier:
            position = invoxia_position_and_battery(self.invoxia_identifier)[0]
            if position:
                return position.datetime.strftime('%Y-%m-%dT%H:%M:%S%z'), position.lat, position.lng
            else:
                return "n/a"
        vehicles_last_position = cache.get('vehicles-last-position')
        if vehicles_last_position:
            return find_vehicle_position(convadis_identifier=self.convadis_identifier,
                                         vehicles_last_position=vehicles_last_position)
        else:
            client = get_oauth2_convadis_rest_client_v2()
            if client:
                try:
                    r_post = client.post(
                        'https://iccom.convadis.ch/api/v1/organizations/%s/vehicles/%s/commands/request-last-position' % (
                            config.CONVADIS_ORG_ID, self.convadis_identifier))
                    r_last = client.get(
                        'https://iccom.convadis.ch/api/v1/organizations/%s/vehicles-last-position' % config.CONVADIS_ORG_ID)
                except TokenExpiredError as e:
                    client = get_oauth2_convadis_rest_client_v2(refresh_token=True)
                    print(e)
                except Exception as e:
                    return "Error: %s" % e
            else:
                client  = get_oauth2_convadis_rest_client_v2(refresh_token=True)
            if client:
                r_post = client.post(
                    'https://iccom.convadis.ch/api/v1/organizations/%s/vehicles/%s/commands/request-last-position' % (
                        config.CONVADIS_ORG_ID, self.convadis_identifier))
                r_last = client.get(
                    'https://iccom.convadis.ch/api/v1/organizations/%s/vehicles-last-position' % config.CONVADIS_ORG_ID)
                text_last = r_last.text
                vehicles_last_position = json.loads(text_last)
                # {'code': 'CLIENT_ID_SECRET_INVALID', 'message': 'The client_id and/or client_secret is invalid.'}
                if 'code' in vehicles_last_position:
                    return "Error: %s" % vehicles_last_position['message']
                # cache 30 seconds
                cache.set('vehicles-last-position', vehicles_last_position, 30)
                return find_vehicle_position(convadis_identifier=self.convadis_identifier,
                                             vehicles_last_position=vehicles_last_position)

                # v_states = client.get(
                #     "https://iccom.convadis.ch/api/v1/organizations/%s/vehicles-last-state" %
                #     config.CONVADIS_ORG_ID)
                # print(v_states)

            return "Error"

    @property
    def address(self):
        if not self.is_connected_to_convadis and not self.invoxia_identifier:
            return "n/a"
        if self.is_connected_to_convadis:
            if not self.convadis_identifier:
                return "n/a Error: convadis id is not set"
        geo_loc_car = self.geo_localisation_of_car
        # if geo_loc_car contains Error just display it
        if isinstance(geo_loc_car, str):
            return geo_loc_car
        position_lon = geo_loc_car[2]
        position_lat = geo_loc_car[1]
        position_time = geo_loc_car[0]

        headers = {
            'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
        }

        url_address = "https://api.openrouteservice.org/geocode/reverse?api_key" \
                      "=%s&point.lon=%s&point.lat=%s" % (
                          config.OPENROUTE_SERVICE_API_KEY, position_lon, position_lat)

        r = requests.get(url_address, headers=headers)
        data = json.loads(r.text)

        time_converter = datetime.strptime(position_time, '%Y-%m-%dT%H:%M:%S%z')
        heure_luxembourg = str(time_converter.astimezone(pytz.timezone('Europe/Luxembourg')))
        if "features" in data:
            address = data["features"][0]['properties']['label']
            return "%s - màj: %s" % (address, heure_luxembourg)
        return data

    @property
    def car_movement(self):
        if not self.is_connected_to_convadis:
            return "n/a"
        if self.is_connected_to_convadis and not self.convadis_identifier:
            return "n/a Error: convadis id is not set"
        client = get_oauth2_convadis_rest_client_v2()
        try:
            r_get = client.get(
                'https://iccom.convadis.ch/api/v1/organizations/%s/vehicles-last-position' % config.CONVADIS_ORG_ID)
        except TokenExpiredError as te:
            print(te)
            get_oauth2_convadis_rest_client_v2(refresh_token=True)
            r_get = client.get(
                'https://iccom.convadis.ch/api/v1/organizations/%s/vehicles-last-position' % config.CONVADIS_ORG_ID)
        speed = json.loads(r_get.text)

        if isinstance(vehicle_speed(self.convadis_identifier, speed), int) and vehicle_speed(self.convadis_identifier,
                                                                                             speed) > 0:
            return "Car is in movement"
        else:
            return "Car is stopped"

    @property
    def pin_codes(self):
        pin_codes: List[str] = []
        for r in self.expensecard_set.all():
            pin_codes.append("%s - %s" % (r.name, r.pin))
        return pin_codes

    def __str__(self):
        if self.vin_number:
            vin = Vin(self.vin_number)
            if vin.validate(self.vin_number):
                # get values in vin annotate_titles to get the full name of the field
                resource_name = " - %s" % self.licence_plate
                for k in vin.annotate_titles:
                    vin.__dict__[k] = vin.annotate_titles[k]
                    if vin.__getattribute__(k) and len(vin.__getattribute__(k)) > 0:
                        resource_name += " %s: %s " % (k, vin.__getattribute__(k))
                return resource_name
            else:
                return '%s - %s (VIN error)' % (self.name, self.licence_plate)
        return '%s - %s' % (self.name, self.licence_plate)

    @property
    def mileage(self):

        if not self.is_connected_to_convadis:
            return "n/a"
        if self.is_connected_to_convadis and not self.convadis_identifier:
            return "n/a Error: convadis id is not set"
        client = get_oauth2_convadis_rest_client()

        r_get = client.get(
            "https://iccom.convadis.ch/api/v1/organizations/%s/vehicles-last-state" % config.CONVADIS_ORG_ID)

        mil = json.loads(r_get.text)

        return "%s km" % vehicle_mileage(self.convadis_identifier, mil)


class ExpenseCard(models.Model):
    class Meta:
        ordering = ['-name']

    name = models.CharField(max_length=20)
    number = models.CharField(max_length=20, default="XX1111")
    pin = models.CharField(max_length=8, default="1111")
    car_link = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return 'Card: %s - %s' % (self.name, self.number)


class MaintenanceFile(models.Model):
    class Meta:
        ordering = ['-file_date']

    file_date = models.DateField()
    description = models.CharField(max_length=50)
    mileage = models.IntegerField(blank=True, null=True)
    file = models.FileField(upload_to=maintenance_file_storage_location)
    car_link = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return 'File: %s - %s' % (self.file_date, self.description)
