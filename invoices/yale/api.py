import random
import string

from constance import config
from yalexs.api import Api
from yalexs.authenticator import Authenticator
from yalexs.authenticator_common import AuthenticationState


class SingleInstanceMetaClass(type):
    def __init__(self, name, bases, dic):
        self.__single_instance = None
        super().__init__(name, bases, dic)

    def __call__(cls, *args, **kwargs):
        if cls.__single_instance:
            return cls.__single_instance
        single_obj = cls.__new__(cls)
        single_obj.__init__(*args, **kwargs)
        cls.__single_instance = single_obj
        return single_obj


class CustomizedYaleSession(metaclass=SingleInstanceMetaClass):

    def __init__(self):
        self.api = Api(timeout=20)
        self.authenticator = Authenticator(self.api,
                                           login_method="email",
                                           username=config.YALE_USERNAME,
                                           password=config.YALE_PASSWORD,
                                           access_token_cache_file="yale_access_token")
        self.identifier = ''.join(random.choices(string.ascii_lowercase, k=5))
        self.authentication = self.authenticator.authenticate()

    def __call__(self):
        return self

    def send_validation(self):
        if self.authentication.state == AuthenticationState.REQUIRES_VALIDATION:
            self.authenticator.send_verification_code()
            return "Successfully sent validation, state is now %s" % self.authentication.state
        return "No need to send verification code as state is %s" % self.authentication.state

    def authenticate(self, validation_code):
        self.authentication = self.authenticator.authenticate()
        if self.authentication.state == AuthenticationState.AUTHENTICATED:
            return "Authenticated %s" % self.authentication.state
        else:
            validation_result = self.authenticator.validate_verification_code(validation_code)
            print(validation_result)
            # Once you have authenticated and validated you can use the access token to make API calls
            # locks = api.get_locks(authentication.access_token) # toto
            self.authentication = self.authenticator.authenticate()
            # lock_activities = api.get_house_activities(authentication.access_token, house_id="") # toto
            return "Authentication %s" % validation_result
        return "Unknown ?"

    def get_house_activities(self):
        if not self.authentication:
            self.authentication = self.authenticator.authenticate()
        return self.api.get_house_activities(self.authentication.access_token,
                                             house_id=config.YALE_HOUSE_ID,
                                             limit=2000)

    def get_authentication_state(self):
        return self.authentication.state


CustomizedYaleSession = CustomizedYaleSession()


def get_yale_house_activities():
    return "Toto"
