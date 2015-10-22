"""Functionality to lookup pricing for endpoints."""
from django.conf import settings
from django.core.urlresolvers import resolve


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
    view = resolve(request.path)

    if view.func not in settings.BITSERV_API_PRICES:
        return settings.BITSERV_DEFAULT_PRICE

    price = settings.BITSERV_API_PRICES[view.func]
    if callable(price):
        return price(request)
    else:
        return price


def api_price(price):
    """Decorator to define a price for an api endpoint.

    NOTE: This decorator MUST be the outermost decorator on an endpoint in
    order for price lookups to succeed. This will be fixed in a future release.

    Args:
        price (int or callable): Static price or method that calculates the
            price for a resource. Method is passed a request object.
    """
    def _wrapped(fn):
        """Save the price in a global API price lookup table."""
        settings.BITSERV_API_PRICES[fn] = price
        return fn
    return _wrapped
