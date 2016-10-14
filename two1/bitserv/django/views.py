"""Added views for a bitserv server."""
from rest_framework import status
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

from . import payment


class PaymentAPIError(Exception):
    """Generic error for exceptions encountered during payment negotiation."""
    pass


class BadParametersError(PaymentAPIError):
    """Raised when a client provides incorrect endpoint parameters."""
    pass


class ChannelViewSet(ViewSet):

    """REST interface for managing payment channels."""

    def list(self, request, format='json'):
        """Return the merchant's public key."""
        return Response(payment.server.identify())

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
            deposit_txid = payment.server.open(params['deposit_tx'], params['redeem_script'])

            # Respond with the deposit transaction id as confirmation
            return Response({'deposit_txid': deposit_txid})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk, format='json'):
        """Returns info about a channel."""
        try:
            return Response(payment.server.status(pk))
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
            payment_txid = payment.server.receive_payment(pk, params['payment_tx'])

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
            payment_txid = payment.server.close(pk, params['signature'])

            return Response({'payment_txid': payment_txid})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
