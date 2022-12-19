import logging
from datetime import datetime, timedelta, timezone

from yalexsfork.authenticator import Authenticator
from yalexsfork.authenticator_common import from_authentication_json, Authentication, AuthenticationState

from invoices.yale.model import get_last_yale_token

_LOGGER = logging.getLogger(__name__)


# def get_oauth2_convadis_rest_client_v2(refresh_token=False):
#     if not refresh_token:
#         token = get_last_token()
#         return OAuth2Session('SUR.lu', token=token)
#     else:
#         oauth_session = OAuth2Session(client=LegacyApplicationClient(client_id=config.CONVADIS_CLIENT_ID))
#         token = oauth_session.fetch_token(
#             token_url=config.CONVADIS_URL,
#             username='username',
#             password='password',
#             client_id=config.CONVADIS_CLIENT_ID,
#             client_secret=config.CONVADIS_SECRET_ID)
#         client = OAuth2Session(config.CONVADIS_CLIENT_ID, token=token)
#         token_saver(token)
#         return client

class CustomizedYaleAuthenticator(Authenticator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._setup_authentication()

    def _setup_authentication(self):
        access_token_cache_token = get_last_yale_token()
        if access_token_cache_token is not None:
            self._authentication = from_authentication_json(access_token_cache_token)
            # If token is to expire within 7 days then print a warning.
            if self._authentication.is_expired():
                _LOGGER.error("Token has expired.")
                self._authentication = Authentication(
                    AuthenticationState.REQUIRES_AUTHENTICATION,
                    install_id=self._install_id,
                )
                # If token is not expired but less then 7 days before it
                # will.
            elif (
                             self._authentication.parsed_expiration_time()
                             - datetime.now(timezone.utc)
                     ) < timedelta(days=7):
                exp_time = self._authentication.access_token_expires
                _LOGGER.warning(
                    "API Token is going to expire at %s "
                    "hours. Deleting file %s will result "
                    "in a new token being requested next"
                    " time",
                    exp_time,
                    access_token_cache_token,
                )
            return
        self._authentication = Authentication(
            AuthenticationState.REQUIRES_AUTHENTICATION, install_id=self._install_id
        )

