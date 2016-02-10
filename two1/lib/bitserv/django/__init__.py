"""Bitserv implementation for Django."""
from django.conf import settings
from .decorator import Payment

payment = Payment(settings.WALLET)
