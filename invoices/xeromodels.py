import datetime

import requests
from django.db import models
from django.utils import timezone

from invoices.xero.exceptions import XeroTokenRefreshError


class XeroToken(models.Model):
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires_at = models.DateTimeField()

    def is_expired(self):
        # Check if the current token is expired
        return timezone.now() >= self.expires_at

    @classmethod
    def get_latest_token(cls):
        # Retrieve the latest token (assuming single-user use case)
        return cls.objects.last()

    @classmethod
    def refresh(cls, xero_client_id, xero_client_secret, xero_refresh_url):
        latest_token = cls.get_latest_token()
        if latest_token and latest_token.is_expired():
            # Refresh the token using latest_token.refresh_token
            # Make a POST request to Xero's token refresh endpoint
            response = requests.post(xero_refresh_url, data={
                'grant_type': 'refresh_token',
                'refresh_token': latest_token.refresh_token,
                'client_id': xero_client_id,
                'client_secret': xero_client_secret,
            })

            data = response.json()
            new_token = cls.objects.create(
                access_token=data['access_token'],
                refresh_token=data['refresh_token'],
                expires_at=timezone.now() + datetime.timedelta(seconds=data['expires_in'])
            )
            return new_token
        elif latest_token is None:
            # Redirect to the Xero authorization URL
            raise XeroTokenRefreshError("No XeroToken found in database")
        return latest_token
