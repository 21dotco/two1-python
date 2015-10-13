"""Custom Permissions for Bitcoin Auth."""
from django.conf import settings

from rest_framework.permissions import BasePermission

from .authentication import PaymentRequiredException


class IsBitcoinAuthenticated(BasePermission):

    """Custom permission class to ensure users are BitcoinAuthenticated.

    A traditional permission class such as IsAuthenticated would
    redirect a user to a 403 Permission Denied Error. Instead of doing
    the traditional door shutting, allow the user to pay the endpoint
    via http payment required (402).
    """

    def has_permission(self, request, view):
        """Check if user is authenticated, if not raise 402."""
        # check for debug/test mode.
        if (request.GET.get("tx") == "paid" or
            request.META.get("HTTP_AUTHORIZATION") == "paidsig") \
                and settings.BITSERV_DEBUG:
            return True
        authenticated = request.user and request.user.is_authenticated()
        if not authenticated:
            raise PaymentRequiredException
        else:
            return authenticated
