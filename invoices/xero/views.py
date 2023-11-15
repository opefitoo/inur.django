import datetime

from django.http import HttpResponse
from django.shortcuts import redirect
from requests_oauthlib import OAuth2Session

from invoices import settings
from invoices.xeromodels import XeroToken


def xero_auth(request):
    xero = OAuth2Session(
        settings.XERO_CLIENT_ID,
        redirect_uri=settings.XERO_REDIRECT_URI,
        scope=settings.XERO_SCOPES
    )
    authorization_url, state = xero.authorization_url(settings.XERO_AUTHORIZATION_URL)

    # Store state in session for CSRF protection
    request.session['oauth_state'] = state
    return redirect(authorization_url)


# views.py


def xero_callback(request):
    xero = OAuth2Session(
        settings.XERO_CLIENT_ID,
        state=request.session['oauth_state'],
        redirect_uri=settings.XERO_REDIRECT_URI
    )
    token = xero.fetch_token(
        settings.XERO_TOKEN_URL,
        client_secret=settings.XERO_CLIENT_SECRET,
        authorization_response=request.build_absolute_uri()
    )

    expires_at = datetime.datetime.now() + datetime.timedelta(seconds=token['expires_in'])

    # Save the token using the new model
    XeroToken.objects.create(
        access_token=token['access_token'],
        refresh_token=token['refresh_token'],
        expires_at=expires_at
    )

    return HttpResponse("Xero authentication successful! go back to the app here: <a href='/'>Home</a>")

