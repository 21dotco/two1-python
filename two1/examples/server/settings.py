"""
Django settings for example project.

Generated by 'django-admin startproject' using Django 1.8.2.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
import sys
import dj_database_url


def str2bool(v):
    """Convert env strings to boolean by matching to known 'True' pattern."""
    return str(v).lower() in ("yes", "true", "t", "1", "on")


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "misc/lib"))

STATIC_ROOT = 'staticfiles'
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'misc/static'),
)

ENDPOINTS_FILE = 'endpoints.json'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '6+y)pxr9jy$7f4kjk1@zk*6lem0$4=^4xekew@7r32=sukb&a!'

BLOCKSPRING_API_KEY = os.environ.get('BLOCKSPRING_API_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = str2bool(os.environ.get('DEBUG', True))

ALLOWED_HOSTS = ['*']

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'rest_framework_swagger',
    'bitcoin_auth'
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

ROOT_URLCONF = 'server.urls'

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
            ],
        },
    },
]

WSGI_APPLICATION = 'server.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {}
}

if os.environ.get('DATABASE_URL'):
    # deployed development
    DATABASES['default'] = dj_database_url.parse(
        os.environ.get('DATABASE_URL')
    )
else:
    # local development
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

STATIC_URL = '/static/'

# Static Serve 402 Configuration
STATIC_SERVE_CONFIG = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'static_serve')
) + '/ss_config.yaml'

# 402 settings
# TODO: Refactor into per API call price
BITSERV_DEFAULT_PAYMENT_ADDRESS = os.environ.get(
    "BITSERV_DEFAULT_PAYMENT_ADDRESS",
    "1BHZExCqojqzmFnyyPEcUMWLiWALJ32Zp5"
)


# In satoshi
BITSERV_DEFAULT_PRICE = int(
    os.environ.get(
        'BITSERV_DEFAULT_PRICE',
        5000
    )
)

# for inclusion in 402 payments, username of the seller.
TWO1_USERNAME = os.environ.get(
    'TWO1_USERNAME', "seller"
)

# endpoint of the bittransfer verifier
BITTRANSFER_VERIFICATION_URL = os.environ.get(
    "BITTRANSFER_VERIFICATION_URL",
    "http://localhost:8000/pool/account/{}/21satoshi/"
)

# allows posting "paid" as tx
BITSERV_DEBUG = True

# Server URL with paid WSJ Subscription
WSJ_PAID_SERVER_URL = os.environ.get(
    "WSJ_PAID_SERVER_URL",
    "http://45.55.0.192:5000/url_to_png"
)

# Azure marketplace creds for MS
# related API calls
AZURE_MARKETPLACE_KEY = os.environ.get(
    "AZURE_MARKETPLACE_KEY"
)

# Twitter related credentials for
# making a social call to yourself
# Docs on creating a new app:
# https://apps.twitter.com/app/new

# HANDLE without the @
TWITTER_HANDLE = os.environ.get(
    "TWITTER_HANDLE"
)
TWITTER_CONSUMER_KEY = os.environ.get(
    "TWITTER_CONSUMER_KEY"
)
TWITTER_CONSUMER_SECRET = os.environ.get(
    "TWITTER_CONSUMER_SECRET"
)
TWITTER_OAUTH_TOKEN = os.environ.get(
    "TWITTER_OAUTH_TOKEN"
)
TWITTER_OAUTH_TOKEN_SECRET = os.environ.get(
    "TWITTER_OAUTH_TOKEN_SECRET"
)

# REST FRAMEWORK
REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'bitcoin_auth.authentication.BasicPaymentRequiredAuthentication',
        'bitcoin_auth.authentication.SessionPaymentRequiredAuthentication',
        'bitcoin_auth.authentication.BitTransferAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'bitcoin_auth.permissions.IsBitcoinAuthenticated',
    ),
    # Set the exeption handler so we can send 402 requests.
    'EXCEPTION_HANDLER': 'bitcoin_auth.exceptions.payment_required_exception_handler'
}


SWAGGER_SETTINGS = {
    'exclude_namespaces': [],
    'api_version': '0.1',
    'enabled_methods': [
        'get',
        'post',
        'put',
        'patch',
        'delete'
    ],
    'is_authenticated': False,
    'is_superuser': False,
    'permission_denied_handler': None,
    'info': {
        'description': 'This is a sample bit-server. ',
        'title': 'API Endpoints',
    },
    'doc_expansion': 'list',
}
