import json
from typing import List
from constance import config
from django.core.cache import cache

from django.db import models
from oauthlib.oauth2 import LegacyApplicationClient, TokenExpiredError
from requests_oauthlib import OAuth2Session


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
        vehicles_last_position = cache.get('vehicles-last-position')
        if vehicles_last_position:
            return find_vehicle_position(self.convadis_identifier, vehicles_last_position)
        else:
            client = get_oauth2_convadis_rest_client()
            if client:
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
    def pin_codes(self):
        pin_codes: List[str] = []
        for r in self.expensecard_set.all():
            pin_codes.append("%s - %s" % (r.name, r.pin))
        return pin_codes

    def __str__(self):
        return '%s - %s' % (self.name, self.licence_plate)


class ExpenseCard(models.Model):
    class Meta:
        ordering = ['-name']

    name = models.CharField(max_length=20)
    number = models.CharField(max_length=20, default="XX1111")
    pin = models.CharField(max_length=8, default="1111")
    car_link = models.ForeignKey(Car, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return 'Card: %s - %s' % (self.name, self.number)
