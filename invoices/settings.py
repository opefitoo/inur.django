"""
Django settings for invoices project.

Generated by 'django-admin startproject' using Django 1.8.1.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'pc_pf1h+5n4h(ayu2)j@2_c+qgumxfa5xeplar6*eq8x745lg!'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django_admin_bootstrapped',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'invoices',
    'ajax_select'
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
)

ROOT_URLCONF = 'invoices.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.core.context_processors.request',
            ],
        },
    },
]

WSGI_APPLICATION = 'invoices.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases
# Parse database configuration from $DATABASE_URL
import dj_database_url
DATABASES = {'default': dj_database_url.config(default='postgres://nursev3:nursev3@localhost:5432/nursev3')}

# Enable Connection Pooling
#DATABASES['default']['ENGINE'] = 'django_postgrespool'
DATABASES['default']['AUTOCOMMIT'] = True

# Honor the 'X-Forwarded-Proto' header for request.is_secure()
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Allow all host headers
ALLOWED_HOSTS = ['*']

# Static asset configuration
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_ROOT= os.path.join(BASE_DIR,'staticfiles/')
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static/'),
)

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Luxembourg'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'

# Simplified static file serving.
# https://warehouse.python.org/project/whitenoise/

STATICFILES_STORAGE = 'whitenoise.django.GzipManifestStaticFilesStorage'

# define the lookup channels in use on the site
AJAX_LOOKUP_CHANNELS = {
    #  simple: search Person.objects.filter(name__icontains=q)
    # 'patient'  : {'model': 'invoices.patient', 'search_field': 'name'},
    # define a custom lookup channel
    #'patientsamoi'   : ('lookups', 'PatientLookup'),
    'patient_du_mois': ('invoices.lookups', 'PatientDuMoisLookup'),
    'private_patient_a_facturer': ('invoices.lookups', 'PrivatePatientDuMoisLookup'),
    'patient'   : ('invoices.lookups', 'PatientLookup'),
    'carecode'   : ('invoices.lookups', 'CareCodeLookup'),
}