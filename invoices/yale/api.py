from constance import config
from yalexs.api import Api
from yalexs.authenticator import Authenticator
from yalexs.authenticator_common import AuthenticationState


def get_yale_house_activities():
    api = Api(timeout=20)
    authenticator = Authenticator(api, login_method="email",
                                  username=config.YALE_USERNAME,
                                  password=config.YALE_PASSWORD,
                                  access_token_cache_file="yale_access_token")

    authentication = authenticator.authenticate()

    # State can be either REQUIRES_VALIDATION, BAD_PASSWORD or AUTHENTICATED
    # You'll need to call different methods to finish authentication process, see below
    state = authentication.state

    # If AuthenticationState is BAD_PASSWORD, that means your login_method, username and password do not match

    # If AuthenticationState is AUTHENTICATED, that means you're authenticated already. If you specify "access_token_cache_file", the authentication is cached in a file. Everytime you try to authenticate again, it'll read from that file and if you're authenticated already, Authenticator won't call Yale Access again as you have a valid access_token

    # If AuthenticationState is REQUIRES_VALIDATION, then you'll need to go through verification process
    # send_verification_code() will send a code to either your phone or email depending on login_method
    if state == AuthenticationState.REQUIRES_VALIDATION:
        authenticator.send_verification_code()

        # Wait for your code and pass it in to validate_verification_code()
        validation_result = authenticator.validate_verification_code(config.YALE_VERIFICATION_CODE)
    # If ValidationResult is INVALID_VERIFICATION_CODE, then you'll need to either enter correct one or resend by calling send_verification_code() again
    # If ValidationResult is VALIDATED, then you'll need to call authenticate() again to finish authentication process
    authentication = authenticator.authenticate()  # toto

    # Once you have authenticated and validated you can use the access token to make API calls
    # locks = api.get_locks(authentication.access_token) # toto
    house_acts = api.get_house_activities(authentication.access_token, house_id="9981165c-d37e-4365-abbf-809c2ba64e82",
                                          limit=2000)  # toto

    # lock_activities = api.get_house_activities(authentication.access_token, house_id="") # toto
    print(house_acts)
    return house_acts
