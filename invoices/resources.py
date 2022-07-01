import json
import requests
from typing import List
from constance import config
from django.core.cache import cache

from django.db import models
from oauthlib.oauth2 import LegacyApplicationClient, TokenExpiredError
from requests_oauthlib import OAuth2Session
from datetime import datetime
from pytz import timezone


def get_last_token():
    if len(ConvadisOAuth2Token.objects.all()) > 0:
        return ConvadisOAuth2Token.objects.first().token
    return None


def token_saver(token):
    ConvadisOAuth2Token.objects.all().delete()
    ConvadisOAuth2Token(token=token).save()


def get_oauth2_convadis_rest_client():
    token = get_last_token()
    client = None
    try:
        if token:
            client = OAuth2Session(config.CONVADIS_CLIENT_ID, token=token)
        else:
            oauth_session = OAuth2Session(client=LegacyApplicationClient(client_id=config.CONVADIS_CLIENT_ID))
            token = oauth_session.fetch_token(
                token_url=config.CONVADIS_URL,
                username='username',
                password='password',
                client_id=config.CONVADIS_CLIENT_ID,
                client_secret=config.CONVADIS_SECRET_ID)
            client = OAuth2Session('SUR.lu', token=token)
            token_saver(token)
    except TokenExpiredError as e:
        oauth_session = OAuth2Session(client=LegacyApplicationClient(client_id=config.CONVADIS_CLIENT_ID))
        token = oauth_session.fetch_token(
            token_url=config.CONVADIS_URL,
            username='username',
            password='password',
            client_id=config.CONVADIS_CLIENT_ID,
            client_secret=config.CONVADIS_SECRET_ID)
        token_saver(token)
        client = OAuth2Session('SUR.lu', token=token)
    finally:
        return client


class ConvadisOAuth2Token(models.Model):
    token = models.JSONField()


def find_vehicle_position(convadis_identifier, vehicles_last_position):
    for vehicle_last_position in vehicles_last_position:
        if vehicle_last_position['vehicleId'] == int(convadis_identifier):
            return vehicle_last_position['timestamp'], vehicle_last_position['lat'], vehicle_last_position['lon']


def vehicle_speed(convadis_identifier, speed):
    for speed in speed:
        if speed['vehicleId'] == int(convadis_identifier):
            return speed['sog']


def vehicle_mileage(convadis_identifier, mil):
    for mil in mil:
        if mil["vehicleId"] == int(convadis_identifier):
            return mil["totalMileage"]["value"]


class Car(models.Model):
    class Meta:
        ordering = ['-name']
        verbose_name = u"Voiture, Clé ou coffre"
        verbose_name_plural = u"Voitures, Clés ou coffres"

    name = models.CharField(max_length=20)
    licence_plate = models.CharField(max_length=8)
    is_connected_to_convadis = models.BooleanField(default=False)
    convadis_identifier = models.CharField(max_length=20, default=None, blank=True, null=True)

    @property
    def geo_localisation_of_car(self):
        if not self.is_connected_to_convadis:
            return "n/a"
        if self.is_connected_to_convadis and not self.convadis_identifier:
            return "n/a Error: convadis id is not set"
        vehicles_last_position = cache.get('vehicles-last-position')
        if vehicles_last_position:
            return find_vehicle_position(self.convadis_identifier, vehicles_last_position)
        else:
            client = get_oauth2_convadis_rest_client()
            if client:
                r_post = client.post(
                    'https://iccom.convadis.ch/api/v1/organizations/%s/vehicles/%s/commands/request-last-position' % (
                        config.CONVADIS_ORG_ID, self.convadis_identifier))
                r_last = client.get(
                    'https://iccom.convadis.ch/api/v1/organizations/%s/vehicles-last-position' % config.CONVADIS_ORG_ID)

                text_last = r_last.text
                vehicles_last_position = json.loads(text_last)
                # cache 30 seconds
                cache.set('vehicles-last-position', vehicles_last_position, 30)
                return find_vehicle_position(self.convadis_identifier, vehicles_last_position)

                # v_states = client.get(
                #     "https://iccom.convadis.ch/api/v1/organizations/%s/vehicles-last-state" %
                #     config.CONVADIS_ORG_ID)
                # print(v_states)

            return "Error"

    @property
    def address(self):
        if not self.is_connected_to_convadis:
            return "n/a"
        if self.is_connected_to_convadis and not self.convadis_identifier:
            return "n/a Error: convadis id is not set"
        geo_loc_car = self.geo_localisation_of_car
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
        heure_luxembourg = str(time_converter.astimezone(timezone('Europe/Luxembourg')))
        address = data["features"][0]['properties']['label']

        return "%s - màj: %s" % (address, heure_luxembourg)

    @property
    def car_movement(self):
        if not self.is_connected_to_convadis:
            return "n/a"
        if self.is_connected_to_convadis and not self.convadis_identifier:
            return "n/a Error: convadis id is not set"
        client = get_oauth2_convadis_rest_client()

        r_get = client.get(
            'https://iccom.convadis.ch/api/v1/organizations/%s/vehicles-last-position' % config.CONVADIS_ORG_ID)

        speed = json.loads(r_get.text)

        if vehicle_speed(self.convadis_identifier, speed) > 1:
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
