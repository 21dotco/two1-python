"""Views for bitcoin_auth."""
from rest_framework import status
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from rest_framework.authentication import BaseAuthentication
from rest_framework.decorators import api_view, authentication_classes
from django.contrib.auth import get_user_model

from two1.lib.bitcoin import Transaction
from two1.lib.bitcoin.utils import bytes_to_str
from .authentication import payment_server
from .models import BitcoinToken


@api_view(['GET'])
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
        balance=request.auth
    )
    token.save()
    return Response(
        {"BitcoinToken": token.key, "balance": token.balance},
        status=status.HTTP_201_CREATED
    )


class PaymentAPIError(Exception):
    pass


class BadParametersError(PaymentAPIError):
    pass


class ChannelViewSet(ViewSet):

    def list(self, request, format='json'):
        """Return the merchant's public key."""
        return Response({'public_key': payment_server.discovery(),
                        'version': payment_server.PROTOCOL_VERSION})

    def create(self, request, format='json'):
        """Open a payment channel.

        Params (json):
            deposit_tx (string): serialized deposit transaction.
            redeem_script (string): serialized redeem script.

        Response (json) 2xx:
            deposit_txid (string): deposit transaction id.
        """
        try:
            # Validate parameters
            params = request.data
            if 'deposit_tx' not in params:
                raise BadParametersError('No deposit provided.')
            if 'redeem_script' not in params:
                raise BadParametersError('No redeem script provided.')

            # Open the payment channel
            deposit_txid = payment_server.open(params['deposit_tx'], params['redeem_script'])

            # Respond with the deposit transaction id as confirmation
            return Response({'deposit_txid': deposit_txid})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk, format='json'):
        """Returns info about a channel."""
        try:
            return Response(payment_server.status(pk))
        except Exception as e:
            error = {'error': str(e)}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk, format='json'):
        """Receive payments inside a payment channel.

        Args:
            pk (string): initial signed deposit transaction id.

        Params (json):
            payment_tx (string): half-signed serialized payment transaction.
        """
        try:
            # Validate parameters
            params = request.data
            if 'payment_tx' not in params:
                raise BadParametersError('No payment provided.')

            # Receive a new payment in the channel
            payment_txid = payment_server.receive_payment(pk, params['payment_tx'])

            # Respond with the payment transaction id as confirmation
            return Response({'payment_txid': payment_txid})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk, format='json'):
        """Close a payment channel.

        Args:
            pk (string): initial signed deposit transaction id.

        Params (json):
            signature (string): deposit_txid signed by customer's private key.

        Response (json) 2xx:
            payment_txid (string): final payment channel transaction id.
        """
        try:
            # Validate parameters
            params = request.data
            if 'signature' not in params:
                raise BadParametersError('No signature provided.')

            # Close the payment channel
            payment_txid = payment_server.close(pk, params['signature'])

            return Response({'payment_txid': payment_txid})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
