"""Custom Authentication For Bitcoin Enabled Applications.

Notes on custom authentication from django-rest-framework
http://www.django-rest-framework.org/api-guide/authentication/#custom-authentication

Classes are implemented to be bitcoin'ified versions of
Rest Framework's Authentication classes.
https://github.com/tomchristie/django-rest-framework/blob/master/rest_framework/authentication.py

Custom Exception Handling:
https://github.com/tomchristie/django-rest-framework/blob/master/docs/api-guide/exceptions.md#custom-exception-handling
"""
import json
import requests

from django.conf import settings
from django.contrib.auth import get_user_model

from rest_framework.authentication import BaseAuthentication

from two1.lib.blockchain.exceptions import DataProviderError
from two1.examples.bitcoin_auth.helpers.bitcoin_auth_provider_helper import (
    BitcoinAuthProvider
)

from .models import BitcoinToken
from .pricing import get_price_for_request
from .exceptions import PaymentRequiredException
from .exceptions import ServiceUnavailable


class BaseBitcoinAuthentication(BaseAuthentication):

    """Basic Bitcoin authentication.

    Attributes:
        bitcoin_provider_helper (BlockchainProvider): provides
            an api & helper methods into the blockchain.
    """

    bitcoin_provider_helper = BitcoinAuthProvider()

    def authenticate(self, request):
        """Passthrough to subclasses authenticate method.

        Args:
            request (request): client side request

        Returns:
            None or Tuple: None or tuple of User, None
                depending if authentication was successfull.
        """
        pass


class BasicPaymentRequiredAuthentication(BaseBitcoinAuthentication):

    """Single authentication using bitcoin.

    Most basic authentication use case, where a
    client uses a single transaction to purchase
    a bitcoin-enabled api call.
    """

    def get_payment_from_header(self, request):
        """Fetch bitcoin transaction from HTTP header.

        Args:
            request (request): a client side request

        Returns:
            str/None: the transaction if exists,
                else None
        """
        if request.META.get("HTTP_BITCOIN_TRANSACTION"):
            return request.META.get("HTTP_BITCOIN_TRANSACTION")
        elif request.GET.get("tx", None):
            return request.GET.get("tx")
        else:
            return None

    def validate_payment(self, tx, request):
        """Validate a bitcoin payment.

        If one of the parameters of the payment are
        invalid, ie, price or address (of merchant),
        raise a 402 error with a message containing
        the appropriate message.

        Example Responses:
            '{"detail":"Incorrect Payout Address","status_code":402}'
            '{"status_code":402,"detail":"Insufficient Payment"}'

        Args:
            tx (TYPE): Description
            request (TYPE): Description

        Returns:
            TYPE: Description

        PaymentRequiredException: If payment is non
            existant or insufficient
        """
        # allow debug transactions
        if settings.BITSERV_DEBUG and tx == "paid":
            return True

        try:
            self.bitcoin_provider_helper.validate_payment(
                tx,
                settings.BITSERV_DEFAULT_PAYMENT_ADDRESS,
                get_price_for_request(request)
            )
            print("Broadcasting transaction: {}".format(
                self.bitcoin_provider_helper.provider.broadcast_transaction(
                    tx
                )
            )
            )
            return True
        except (ValueError, DataProviderError) as e:
            raise PaymentRequiredException(e)

    def authenticate(self, request):
        """Handle bitcoin authentication.

        Args:
            request (request): request object

        Raises:
            PaymentRequiredException: If payment is non
                existant or insufficient
        """
        print("started: BasicPaymentRequiredAuthentication")
        tx = self.get_payment_from_header(request)
        if not tx:
            return None
        if not self.validate_payment(tx, request):
            return PaymentRequiredException
        else:
            if not (settings.BITSERV_DEBUG and tx == "paid"):
                transaction, _ = BitcoinAuthProvider.transaction_hex_str_to_tx(
                    tx
                )
                sso_user, created = get_user_model().objects.get_or_create(
                    username=transaction.hash
                )
                if not created:
                    # we should not have any user that has already been created
                    # in this authentication class, given an username (txid)
                    # should be uniuqe per endpoint use.
                    raise PaymentRequiredException("Double Spend Detected")
                return (sso_user, transaction.outputs[0].value)


class SessionPaymentRequiredAuthentication(BaseBitcoinAuthentication):

    """Session like authentication using bitcoin.

    Current implemention will be using tokens,
    can be extended in the future to support
    payment-channels.
    """

    @staticmethod
    def get_bitcoin_token_from_header(request):
        """Get bitcoin token from HTTP header."""
        token = request.META.get("HTTP_BITCOIN_TOKEN")
        return token

    def authenticate(self, request):
        """Handle bitcoin-session authentication.

        Per each payment, charge a balance (balance
        of each endpoint) to the token until it's no
        longer solvent. In that case raise another
        PaymentRequiredException.

        Args:
            request (request): request object

        Raises:
            PaymentRequiredException: If payment is non
                existant or insufficient
        """
        # check to see if header already includes a bitcoin token
        # for a valid session
        print('started: SessionPaymentRequiredAuthentication')
        bitcoin_token = self.get_bitcoin_token_from_header(request)
        if not bitcoin_token:
            return None
        else:
            try:
                bitcoin_token = BitcoinToken.objects.get(key=bitcoin_token)
                if bitcoin_token.charge(get_price_for_request(request)):
                    return (bitcoin_token.user, bitcoin_token)
                else:
                    raise PaymentRequiredException("Insufficient Funds")
            except BitcoinToken.DoesNotExist:
                raise PaymentRequiredException("Invalid BitcoinToken")


class BitChequeAuthentication(BaseAuthentication):

    """Authentication using Bitcoin-Cheque (off-chain)."""

    @staticmethod
    def get_bitcheque_from_header(request):
        """Get bitcoin-cheque from HTTP headers."""
        return (
            request.META.get("HTTP_BITCOIN_CHEQUE"),
            request.META.get("HTTP_AUTHORIZATION")
            )

    def authenticate(self, request):
        """Authenticate using Bitcoin-Cheque.

        Strip headers for Bitcoin-Cheque and signature
        of the check, send the data to a Bitcoin-Cheque
        verifier (ie: 21.co server), and if that response
        is ok, serve the client.

        Args:
            request (request): a client side request

        Raises:
            PaymentRequiredException: if malformed / insufficient
                / non existant bitcheque.
        """
        print("started: BitChequeAuthentication")
        bitcheque, signature = self.get_bitcheque_from_header(request)
        if not bitcheque:
            return None
        if not bitcheque:
            raise PaymentRequiredException
        else:
            print("cheque: {} \nsignature: {}".format(
                    bitcheque, signature
                )
            )
            # before verifiying with a 3rd party server,
            # verify that the amount sent in the cheque
            # is correct.
            try:
                if not json.loads(bitcheque)["amount"] == \
                        get_price_for_request(request):
                    raise PaymentRequiredException("Insufficient Payment")
            except ValueError:
                raise PaymentRequiredException
            # now verify with server that cheque is valid
            # else raise another PaymentRequiredException.
            if self.verify_cheque(bitcheque, signature):
                user, created = get_user_model().objects.get_or_create(
                    username=json.loads(bitcheque)["payer"]
                )
                return (user, bitcheque)
            else:
                raise PaymentRequiredException

    def verify_cheque(self, bitcheque, signature):
        """Verify that cheque is valid.

        Done via 3rd party server.

        Args:
            bitcheque (str): bitcoin cheque
            signature (TYPE): signature on cheque
        """
        if settings.BITSERV_DEBUG and signature == "paidsig":
            return True

        try:
            verification_response = requests.post(
                settings.BITCHEQUE_VERIFICIATION_URL.format(
                    settings.TWO1_USERNAME
                ),
                data=json.dumps({
                    "bitcheque": bitcheque,
                    "signature": signature
                }),
                headers={'content-type': 'application/json'}
            )
            if verification_response.ok:
                return True
            else:
                if "message" in verification_response.text:
                    raise PaymentRequiredException(
                        verification_response.json()["message"]
                    )
                else:
                    raise ServiceUnavailable
        except requests.ConnectionError:
            return False
