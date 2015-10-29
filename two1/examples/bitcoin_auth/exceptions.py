"""Custom exception handling for Bitcoin Auth."""
from django.conf import settings

from rest_framework import status
from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException

from .pricing import get_price_for_request


def payment_required_exception_handler(exc, context):
    """Custom exception handling for PaymentRequiredException."""
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)
    # Now add the HTTP status code to the response.
    if response is not None:
        response.data['status_code'] = response.status_code
        if response.status_code == PaymentRequiredException.status_code:
            response["Bitcoin-Address"] = \
                settings.BITSERV_DEFAULT_PAYMENT_ADDRESS
            response["Bitcoin-Micropayment-Server"] = \
                context["request"]._request.scheme + "://" + \
                context["request"]._request.get_host() + \
                settings.DEFAULT_PAYMENT_CHANNEL_PATH
            response["Price"] = \
                get_price_for_request(
                    context['request']
                )
            response['Username'] = settings.TWO1_USERNAME
    return response


class PaymentRequiredException(APIException):

    """402 Bitcoin Enabled exception."""

    status_code = status.HTTP_402_PAYMENT_REQUIRED
    default_detail = "Payment Required"


class ServiceUnavailable(APIException):

    """503 Service Unavailable exception."""

    status_code = 503
    default_detail = 'Service temporarily unavailable, try again later.'
