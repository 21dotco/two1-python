"""Flask bitserv payment library for selling 402 API endpoints."""
from flask import request
from functools import wraps
from werkzeug.exceptions import HTTPException, BadRequest
from .methods import OnChain, PaymentChannel


class PaymentRequiredException(HTTPException):

    """Payment required exception."""

    code = 402

    def get_body(self, context):
        """402 response body."""
        return 'Payment Required'

    def get_headers(self, context):
        """402 response headers."""
        payment_headers = self.description
        return payment_headers


class Payment:

    """Class to store merchant settings."""

    def __init__(self, app, db=None, default_price=None, default_address=None,
                 default_micro_server='/payment'):
        """Configure bitserv settings.

        Args:
            app (flask.Flask): a flask app to wrap payment handling around.
        """
        self.default_price = default_price
        self.default_address = default_address
        self.default_micro_server = default_micro_server
        self.allowed_methods = [OnChain(db), PaymentChannel(app, db)]

    def required(self, price=None, address=None, micro_server=None):
        """API route decorator to request payment for a resource.

        This function stores the resource price in a closure. It will verify
        the validity of a payment, and allow access to the resource if the
        payment is successfully accepted.

        Usage:
            @app.route('/myroute')
            @payment.required(100, '1MDxJYsp4q4P46RiigaGzrdyi3dsNWCTaR')

        Raises:
            PaymentRequiredException: HTTP 402 response with payment headers.
        """
        def decorator(fn):
            @wraps(fn)
            def _fn(*args, **kwargs):
                # Get headers for initial 402 response
                payment_headers = {}
                for method in self.allowed_methods:
                    payment_headers.update(method.get_402_headers(
                        price=price or self.default_price,
                        micro_server=micro_server or self.default_micro_server,
                        address=address or self.default_address))

                # Continue to the API view if payment is valid
                if self.is_valid_payment(request.headers, payment_headers):
                    return fn(*args, **kwargs)
                else:
                    raise PaymentRequiredException(payment_headers)
            return _fn
        return decorator

    def is_valid_payment(self, request_headers, payment_headers):
        """Validate the payment information received in the request headers.

        Args:
            request_headers (dict): Headers sent by client with their request.
            payment_headers (dict): Required headers to verify the client's
                request against.
        """
        for method in self.allowed_methods:
            if method.should_redeem(request_headers):
                try:
                    v = method.redeem_payment(request_headers, payment_headers)
                except Exception as e:
                    print(str(e))  # TODO better logging for errors
                    raise BadRequest(str(e))
                return v
        return False
