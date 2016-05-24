"""Bitserv implementation for Django."""
try:
    import django  # noqa
    import rest_framework  # noqa
except ImportError:
    raise ImportError(
        '''21 Django integration requires the following packages:

django~=1.8.0
djangorestframework==3.2.3

Please install them with pip before continuing.'''
    )

from django.conf import settings
from .decorator import Payment

payment = Payment(settings.WALLET)
