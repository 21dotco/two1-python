"""Custom Authentication For Bitcoin Enabled Applications.

Notes on custom authentication from django-rest-framework
http://www.django-rest-framework.org/api-guide/authentication/#custom-authentication

Classes are implemented to be bitcoin'ified versions of
Rest Framework's Authentication classes.
https://github.com/tomchristie/django-rest-framework/blob/master/rest_framework/authentication.py

Custom Exception Handling:
https://github.com/tomchristie/django-rest-framework/blob/master/docs/api-guide/exceptions.md#custom-exception-handling
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from rest_framework.authentication import BaseAuthentication

from two1.lib.blockchain.exceptions import DataProviderError
from two1.examples.bitcoin_auth.helpers.chain_provider_helper import (
    ChainProviderHelper
)

from .models import BitcoinToken
from .pricing import get_price_for_request
from .exceptions import PaymentRequiredException


class BaseBitcoinAuthentication(BaseAuthentication):

    """Basic Bitcoin authentication.

    Attributes:
        bitcoin_provider_helper (BlockchainProvider): provides
            an api & helper methods into the blockchain.
    """

    bitcoin_provider_helper = ChainProviderHelper()

    @staticmethod
    def get_payment_from_header(request):
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

    def authenticate(self, request):
        """Handle bitcoin authentication.

        Args:
            request (request): request object

        Raises:
            PaymentRequiredException: If payment is non
                existant or insufficient
        """
        tx = self.get_payment_from_header(request)
        if not tx:
            raise PaymentRequiredException
        if not self.validate_payment(tx, request):
            return None
        else:
            if not (settings.BITSERV_DEBUG and tx == "paid"):
                User = get_user_model()
                transaction, _ = ChainProviderHelper.transaction_hex_str_to_tx(
                    tx
                )
                paying_user = User(username=(transaction.hash))
                try:
                    paying_user.validate_unique()
                    paying_user.save()
                except ValidationError:
                    # Means that user is trying to spend the same
                    # transaction twice! This is a double spend.
                    raise PaymentRequiredException("Double Spend Detected")
                return (paying_user, transaction.outputs[0].value)


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
