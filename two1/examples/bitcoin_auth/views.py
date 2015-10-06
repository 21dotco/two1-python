"""Views for bitcoin_auth."""
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.decorators import authentication_classes

from .models import BitcoinToken
from .authentication import BasicPaymentRequiredAuthentication


@api_view(['GET'])
@authentication_classes([BasicPaymentRequiredAuthentication])
def token(request):
    """Request a BitcoinToken.

    If a valid payment is attached to the request,
    create a user for the client (username = txid)
    and then create a BitcoinToken for that client
    with a balance of the clients payment.

    Args:
        request (request): request object, if
            authentication was successful, the request
            object incldues an .auth attribute which is
            the amount paid passed back via
            BasicPaymentRequiredAuthentication, as well
            as a user attribute which is linked to the
            currently active user as the .user attribute.

    Returns:
        Repsone: HTTP Response with token or error.
    """
    token = BitcoinToken(
        user=request.user,
        balance=request.auth * 5
    )
    token.save()
    return Response(
        {"BitcoinToken": token.key, "balance": token.balance},
        status=status.HTTP_201_CREATED
    )
