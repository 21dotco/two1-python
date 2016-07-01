"""Django bitserv payment library for selling 402 API endpoints."""
import os
from functools import wraps
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ParseError
import two1.bitserv as bitserv


class PaymentRequiredResponse(Response):

    """Payment required response."""

    status_code = status.HTTP_402_PAYMENT_REQUIRED
    data = 'Payment Required'

    def __init__(self, *args, **kwargs):
        super().__init__(PaymentRequiredResponse.data, *args, **kwargs)


class Payment:

    """Class to store merchant settings."""

    def __init__(self, wallet, allowed_methods=None, zeroconf=False, sync_period=10):
        """Configure bitserv settings.

        Args:
            wallet (two1.wallet.Wallet): The merchant's wallet instance.
        """
        from .models import PaymentChannel, PaymentChannelSpend, BlockchainTransaction
        if allowed_methods is None:
            pc_db = bitserv.DatabaseDjango(PaymentChannel, PaymentChannelSpend)
            self.server = bitserv.PaymentServer(wallet, pc_db, zeroconf=zeroconf, sync_period=sync_period)
            self.allowed_methods = [
                bitserv.PaymentChannel(self.server, '/payments/channel'),
                bitserv.OnChain(wallet, bitserv.OnChainDjango(BlockchainTransaction)),
                bitserv.BitTransfer(wallet, username=os.environ.get('TWO1_USERNAME', None))]

    def required(self, price, **kwargs):
        """API route decorator to request payment for a resource.

        This function stores the resource price in a closure. It will verify
        the validity of a payment, and allow access to the resource if the
        payment is successfully accepted.
        """
        def decorator(fn):
            """Validates payment and returns the original API route."""
            @wraps(fn)
            def _fn(request, *fn_args, **fn_kwargs):
                # Calculate resource cost
                nonlocal price
                _price = price(request) if callable(price) else price

                # Need better way to pass server url to payment methods (FIXME)
                if 'server_url' not in kwargs:
                    kwargs.update({'server_url': request.scheme + '://' + request.get_host()})

                # Convert from django META object to normal header format
                headers = {}
                for k, v in request.META.items():
                    if 'HTTP_' in k:
                        header = '-'.join([w.title() for w in k.split('_')[1:]])
                        headers[header] = v

                # Continue to the API view if payment is valid or price is 0
                if _price == 0 or self.contains_payment(_price, headers, **kwargs):
                    return fn(request, *fn_args, **fn_kwargs)
                else:
                    # Get headers for initial 402 response
                    payment_headers = {}
                    for method in self.allowed_methods:
                        payment_headers.update(method.get_402_headers(_price, **kwargs))
                    return PaymentRequiredResponse(headers=payment_headers)
            return _fn
        return decorator

    def contains_payment(self, price, request_headers, **kwargs):
        """Validate the payment information received in the request headers.

        Args:
            price (int): The price the user must pay for the resource.
            request_headers (dict): Headers sent by client with their request.
            keyword args: Any other headers needed to verify payment.
        Returns:
            (bool): True if payment is valid,
                False if no payment attached (402 initiation).
        Raises:
            ParseError: If request is malformed.
        """
        for method in self.allowed_methods:
            if method.should_redeem(request_headers):
                try:
                    v = method.redeem_payment(price, request_headers, **kwargs)
                except Exception as e:
                    raise ParseError(str(e))
                return v
        return False
