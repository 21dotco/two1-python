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

from two1.lib.wallet import Wallet, Two1Wallet
from two1.commands.config import TWO1_PROVIDER_HOST
from two1.lib.bitserv import PaymentServer, DatabaseDjango
from two1.lib.blockchain.twentyone_provider import TwentyOneProvider
from two1.lib.blockchain.exceptions import DataProviderError
from two1.examples.bitcoin_auth.helpers.bitcoin_auth_provider_helper import (
    BitcoinAuthProvider
)

from .models import BitcoinToken, PaymentChannel, PaymentChannelSpend
from .pricing import get_price_for_request
from .exceptions import PaymentRequiredException
from .exceptions import ServiceUnavailable

if settings.WALLET_MNEMONIC:
    dp = TwentyOneProvider(TWO1_PROVIDER_HOST)
    wallet = Two1Wallet.import_from_mnemonic(dp, settings.WALLET_MNEMONIC)
else:
    wallet = Wallet()
payment_server = PaymentServer(
    wallet, DatabaseDjango(PaymentChannel, PaymentChannelSpend))


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
            else:
                debug_user, created = get_user_model().objects.get_or_create(username='debug_user')
                return (debug_user, None)


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


class BitTransferAuthentication(BaseAuthentication):

    """Authentication using Bitcoin-Transfer (off-chain)."""

    @staticmethod
    def get_bittransfer_from_header(request):
        """Get bitcoin-transfer from HTTP headers."""
        return (
            request.META.get("HTTP_BITCOIN_TRANSFER"),
            request.META.get("HTTP_AUTHORIZATION")
            )

    def authenticate(self, request):
        """Authenticate using Bitcoin-Transfer.

        Strip headers for Bitcoin-Transfer and signature
        of the check, send the data to a Bitcoin-Transfer
        verifier (ie: 21.co server), and if that response
        is ok, serve the client.

        Args:
            request (request): a client side request

        Raises:
            PaymentRequiredException: if malformed / insufficient
                / non existant bittransfer.
        """
        print("started: BitTransferAuthentication")
        bittransfer, signature = self.get_bittransfer_from_header(request)
        if not bittransfer:
            return None
        if not bittransfer:
            raise PaymentRequiredException
        else:
            print("transfer: {} \nsignature: {}".format(
                    bittransfer, signature
                )
            )
            # before verifiying with a 3rd party server,
            # verify that the amount sent in the transfer
            # is correct.
            try:
                if not json.loads(bittransfer)["amount"] == \
                        get_price_for_request(request):
                    raise PaymentRequiredException("Insufficient Payment")
            except ValueError:
                raise PaymentRequiredException
            # now verify with server that transfer is valid
            # else raise another PaymentRequiredException.
            if self.verify_transfer(bittransfer, signature):
                user, created = get_user_model().objects.get_or_create(
                    username=json.loads(bittransfer)["payer"]
                )
                return (user, bittransfer)
            else:
                raise PaymentRequiredException

    def verify_transfer(self, bittransfer, signature):
        """Verify that transfer is valid.

        Done via 3rd party server.

        Args:
            bittransfer (str): bitcoin transfer
            signature (TYPE): signature on transfer
        """
        if settings.BITSERV_DEBUG and signature == "paidsig":
            return True

        try:
            verification_response = requests.post(
                settings.BITTRANSFER_VERIFICATION_URL.format(
                    settings.TWO1_USERNAME
                ),
                data=json.dumps({
                    "bittransfer": bittransfer,
                    "signature": signature
                }),
                headers={'content-type': 'application/json'}
            )
            if verification_response.ok:
                return True
            else:
                if "error" in verification_response.text:
                    raise PaymentRequiredException(
                        verification_response.json()["error"]
                    )
                else:
                    raise ServiceUnavailable
        except requests.ConnectionError:
            return False


class PaymentServerAuthentication(BaseBitcoinAuthentication):

    """Authenticates a payment within a payment channel.

    Attempts to use the transaction id of a payment to look up an existing
    payment channel, and see if the payment can be redeemed to pay for the
    requested resource.
    """

    def __init__(self):
        """Initialize payment channel authentization module.

        This specifically creates a re-usable `payment_channel_user` for auth
        purposes, as channels rely on other metrics for payment authentication.
        """
        self.pc_user, _ = get_user_model().objects.get_or_create(
            username='payment_channel_user')

    def authenticate(self, request):
        """Handle payment channel authentication.

        Args:
            request (request): object representing the client's http request

        Raises:
            PaymentRequiredException: payment is nonexistent or insufficient
        """
        payment_header = 'HTTP_BITCOIN_PAYMENT_CHANNEL_TOKEN'
        # Whitelist payment channel route
        if settings.DEFAULT_PAYMENT_CHANNEL_PATH in request._request.path:
            return (self.pc_user, None)
        # Do not authenticate if no payment channel token exists
        if payment_header not in request.META:
            return None

        validation = None
        try:
            # Redeem the transaction in its payment channel
            paid_amount = payment_server.redeem(request.META[payment_header])
            # Verify the amount of the payment against the resource price
            if paid_amount >= int(get_price_for_request(request)):
                validation = (self.pc_user, paid_amount)
        finally:
            return validation
