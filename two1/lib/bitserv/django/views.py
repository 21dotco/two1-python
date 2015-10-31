from rest_framework import status
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response

from two1.lib.bitcoin import Transaction
from two1.lib.bitcoin.utils import bytes_to_str

from . import payment


class PaymentAPIError(Exception):
    pass


class BadParametersError(PaymentAPIError):
    pass


class ChannelViewSet(ViewSet):

    def list(self, request, format='json'):
        """Return the merchant's public key."""
        return Response({'public_key': payment.server.discovery()})

    def create(self, request, format='json'):
        """Initialize the payment channel handshake.

        Params (query):
            refund_tx (string): half-signed serialized refund transaction

        Response (json) 2xx:
            refund_tx (string): fully-signed serialized refund transaction
        """
        try:
            params = request.data
            # Validate parameters
            if 'refund_tx' not in params:
                raise BadParametersError('No refund provided.')

            # Initialize the payment channel
            refund_tx = Transaction.from_hex(params['refund_tx'])
            payment.server.initialize_handshake(refund_tx)

            # Respond with the fully-signed refund transaction
            success = {'refund_tx': bytes_to_str(bytes(refund_tx))}
            return Response(success)
        except Exception as e:
            error = {'error': str(e)}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk, format='json'):
        """Returns info about a channel."""
        try:
            return Response(payment.server.status(pk))
        except Exception as e:
            error = {'error': str(e)}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, pk, format='json'):
        """Complete the payment channel handshake or receive payments.

        Args:
            pk (string): initial signed deposit transaction id

        Params (json) (one of the following):
            deposit_tx (string): half-signed serialized deposit transaction
            payment_tx (string):  half-signed serialized payment transaction
        """
        try:
            params = request.data
            if 'deposit_tx' in params:
                # Complete the handshake using the received deposit
                deposit_tx = Transaction.from_hex(params['deposit_tx'])
                payment.server.complete_handshake(pk, deposit_tx)
                return Response()
            elif 'payment_tx' in params:
                # Receive a payment in the channel using the received payment
                payment_tx = Transaction.from_hex(params['payment_tx'])
                payment.server.receive_payment(pk, payment_tx)
                return Response({'payment_txid': str(payment_tx.hash)})
            else:
                raise KeyError('No deposit or payment received.')
        except Exception as e:
            error = {'error': str(e)}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk, format='json'):
        """Close a payment channel.

        Args:
            pk (string): initial signed deposit transaction id

        Response (json) 2xx:
            payment_txid (string): final payment channel transaction id
        """
        try:
            payment_txid = payment.server.close(pk)
            return Response({'payment_txid': payment_txid})
        except Exception as e:
            error = {'error': str(e)}
            return Response(error, status=status.HTTP_400_BAD_REQUEST)
