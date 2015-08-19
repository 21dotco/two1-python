from django.http import HttpResponse
from lib.chain   import BitcoinInterface
from django.conf import settings
# import qrcode
# import base64
# from io import BytesIO


from django.contrib.auth.models import User
from rest_framework import authentication
from rest_framework import exceptions
from rest_framework.views import exception_handler
from rest_framework import status
from rest_framework.response import Response

CAPI = BitcoinInterface()
payment_required_body_text = "Payment Required"


# This is the applications exception handler, we will write our exception
# HTTP responses here.
def PaymentRequiredExceptionHandler(exc, context):
    # Get the default exception response from the rest framework.
    response = exception_handler(exc, context)

    # Override with custom status code, if needed
    if hasattr(exc,'status_code'):
        response = HttpResponse(exc, status=exc.status_code)

    # Override with 402, if needed
    if shouldBeConfiguredFor402(exc, response):
        response = configureFor402(
            response,
            exc.paymentInfo['price'],
            exc.paymentInfo['address']
        )

    return response


def shouldBeConfiguredFor402(exc, response):
    return hasattr(exc, 'paymentInfo') and exc.paymentInfo['price'] is not 0

def configureFor402(response, price, address):
    # update status code
    response.status_code = status.HTTP_402_PAYMENT_REQUIRED

    # Set payment headers
    response["Bitcoin-Address"] = address
    response["Price"] = price

    # TODO: Set quote persistence headers
    # response["Price-Token-Expiration"]
    # response["Price-Token"]

    return response


class PaymentRequiredAuthentication(authentication.BaseAuthentication):

    # Entry point for verification
    def authenticate(self, request):
        # Check the transaction and get the state
        tx = self.getTransactionFor(request)

        # No payment headers sent
        if not tx:
            raise self.paymentRequiredException(
                request, payment_required_body_text)

        # Payment verified
        elif self.validatePayment(tx, request):
            print("got paid with: %s" % self.getTransaction(request))
            return None

        # Bad transaction sent by client, or error verifying transaction
        else:
            raise self.paymentRequiredException(
                request, payment_required_body_text)

    # This can be overridden by a subclass to support dynamic prices.
    # NOTE: this method should be 100% deterministic or transaction
    # verification will fail.
    def getQuoteFor(self, request):
        # Use Default Price
        return getattr(settings, 'BITSERV_DEFAULT_PRICE')

    # This can be overridden by a subclass to support generated addresses
    # NOTE: this method should be 100% deterministic or transaction
    # verification will fail.
    def getAddressFor(self, request):
        # Use Default Address
        return getattr(settings, 'BITSERV_DEFAULT_PAYMENT_ADDRESS')

    def validatePayment(self, tx, request):
        if getattr(settings, 'BITSERV_DEBUG') & (tx == "paid"):
            return True

        # Verify Transaction with BitcoinInterface.
        # The tx can be a txId or a tx
        return CAPI.check_payment(
            tx,
            self.getAddressFor(request),
            self.getQuoteFor(request)
        )

    def getTransactionFor(self, request):
        # 1. Header
        # This will only use the Header eventually. All other accepts are for
        # testing
        if request.META.get("HTTP_BITCOIN_TRANSACTION"):
            return request.META.get("HTTP_BITCOIN_TRANSACTION")

        # 2. Query
        elif "tx" in request.GET:
            return request.GET["tx"]
        else:
            return None

    def paymentRequiredException(self, request, message):
        exe = exceptions.AuthenticationFailed(payment_required_body_text)

        # TODO: Validate outputs...
        exe.paymentInfo = {
            'price': self.getQuoteFor(request),
            'address': self.getAddressFor(request),
        }
        return exe
