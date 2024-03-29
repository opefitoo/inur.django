from threading import local

from asgiref.local import Local
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

USER_ATTR_NAME = getattr(settings, 'LOCAL_USER_ATTR_NAME', '_current_user')

_thread_locals = Local()


def _do_set_current_user(user_fun):
    setattr(_thread_locals, USER_ATTR_NAME, user_fun.__get__(user_fun, local))


def _set_current_user(user=None):
    '''
    Sets current user in local thread.

    Can be used as a hook e.g. for shell jobs (when request object is not
    available).
    '''
    _do_set_current_user(lambda self: user)


class ThreadLocalUserMiddleware(MiddlewareMixin):

    # def __init__(self, get_response):
    #     self.get_response = get_response

    def process_request(self, request):
        # request.user closure; asserts laziness;
        # memorization is implemented in
        # request.user (non-data descriptor)
        _do_set_current_user(lambda self: getattr(request, 'user', None))
        response = self.get_response(request)
        return response

    def __init__(self, get_response):
        if get_response is None:
            raise ValueError('get_response must be provided.')
        self.get_response = get_response
        self._async_check()
        super().__init__(get_response)

    def __call__(self, request):
        _do_set_current_user(lambda self: getattr(request, 'user', None))
        response = self.get_response(request)
        return response


def get_current_user():
    current_user = getattr(_thread_locals, USER_ATTR_NAME, None)
    if callable(current_user):
        return current_user()
    return current_user


def get_current_authenticated_user():
    current_user = get_current_user()
    if isinstance(current_user, AnonymousUser):
        return None
    if current_user:
        return current_user.id
    return None

class FirstLoginMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from decouple import config
        INITIAL_EMAIL = config('INITIAL_EMAIL', None)
        if request.user and request.user.is_authenticated and INITIAL_EMAIL and INITIAL_EMAIL == request.user.email:
            if request.path not in ['/password_change/', '/logout/']:
                return redirect('password_change')
        response = self.get_response(request)
        return response


class SetTokenCookieMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        auth_token = request.session.get('auth_token')
        if auth_token:
            response.set_cookie('auth_token', auth_token)
        return response
