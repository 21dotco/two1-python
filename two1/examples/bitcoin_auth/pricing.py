"""Functionality to lookup pricing for endpoints."""
from django.conf import settings


def get_price_for_request(request):
    """Lookup payment amount for an endpoint.

    This information can be provided by a YAML, a
    dynamic pricing equation, etc.

    Args:
        request (request): request object

    Returns:
        (int): satoshi cost of endpoint
    """
    print("Looking up price for {}".format(request.path))
    return settings.BITSERV_DEFAULT_PRICE
