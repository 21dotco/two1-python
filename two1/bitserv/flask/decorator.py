"""Flask bitserv payment library for selling 402 API endpoints."""
import re
from functools import wraps
from urllib.parse import urlparse
from flask import jsonify, request, views
from werkzeug.exceptions import HTTPException, BadRequest, NotFound

from ..payment_methods import OnChain, PaymentChannel, BitTransfer
from ..payment_server import PaymentServer, PaymentChannelNotFoundError


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


class PaymentAPIError(Exception):
    """Generic error for exceptions encountered during payment negotiation."""
    pass


class BadParametersError(PaymentAPIError):
    """Raised when a client provides incorrect endpoint parameters."""
    pass


class Payment:

    """Class to store merchant settings."""

    def __init__(self, app, wallet, allowed_methods=None, zeroconf=True, sync_period=600,
                 endpoint='/payment', db_dir=None, username=None):
        """Configure bitserv settings.

        Args:
            app (flask.Flask): A flask app to wrap payment handling around.
            wallet (two1.wallet.Wallet): The merchant's wallet instance.
            allowed_methods (list): A custom set of bitserv.payment_methods.py
                instances to allow clients to use for payment.
            zeroconf (bool): Whether to allow zero-confirmation transactions.
            sync_period (int): The interval (in seconds) at which to sync
                outstanding payment channel statuses.
            endpoint (str): Custom endpoint name where the payment channel
                server operates.
        """
        if allowed_methods is None:
            self.allowed_methods = [
                PaymentChannel(*flask_channel_adapter(app, PaymentServer(
                    wallet, zeroconf=zeroconf, sync_period=sync_period, db_dir=db_dir
                ), endpoint=endpoint)),
                OnChain(wallet, db_dir=db_dir),
                BitTransfer(wallet, username=username)
            ]
            # Sync payment channels server on startup
            self.allowed_methods[0].server.sync()

    def required(self, price, **kwargs):
        """API route decorator to request payment for a resource.

        This function stores the resource price in a closure. It will verify
        the validity of a payment, and allow access to the resource if the
        payment is successfully accepted.
        """
        def decorator(fn):
            """Validates payment and returns the original API route."""
            @wraps(fn)
            def _fn(*fn_args, **fn_kwargs):
                # Calculate resource cost
                nonlocal price
                _price = price(request) if callable(price) else price

                # Need better way to pass server url to payment methods (FIXME)
                if 'server_url' not in kwargs:
                    url = urlparse(request.url_root)
                    kwargs.update({'server_url': url.scheme + '://' + url.netloc})

                # Continue to the API view if payment is valid or price is 0
                if _price == 0 or self.is_valid_payment(_price, request.headers, **kwargs):
                    return fn(*fn_args, **fn_kwargs)
                else:
                    # Get headers for initial 402 response
                    payment_headers = {}
                    for method in self.allowed_methods:
                        payment_headers.update(method.get_402_headers(_price, **kwargs))
                    raise PaymentRequiredException(payment_headers)
            return _fn
        return decorator

    def is_valid_payment(self, price, request_headers, **kwargs):
        """Validate the payment information received in the request headers.

        Args:
            price (int): The price the user must pay for the resource.
            request_headers (dict): Headers sent by client with their request.
            keyword args: Any other headers needed to verify payment.
        Returns:
            (bool): Whether or not the payment is deemed valid.
        """
        for method in self.allowed_methods:
            if method.should_redeem(request_headers):
                try:
                    v = method.redeem_payment(price, request_headers, **kwargs)
                except Exception as e:
                    raise BadRequest(str(e))
                return v
        return False


def flask_channel_adapter(app, server, endpoint='/payment'):
    """Initialize the Flask views with RESTful access to the Channel."""
    pmt_view = Channel.as_view('channel', server)

    # Verify endpoint format
    if not re.search('^\/\w+$', endpoint):
        raise BadParametersError('Invalid flask endpoint provided to payment decorator.')
    app.add_url_rule(endpoint, defaults={'deposit_txid': None},
                     view_func=pmt_view, methods=('GET',))
    app.add_url_rule(endpoint, view_func=pmt_view, methods=('POST',))
    app.add_url_rule(endpoint + '/<deposit_txid>', view_func=pmt_view,
                     methods=('GET', 'PUT', 'DELETE'))
    return server, endpoint


class Channel(views.MethodView):

    """REST interface for managing payment channels."""

    def __init__(self, server):
        """Initialize the channel view with a PaymentServer object."""
        self.server = server

    def get(self, deposit_txid):
        """Return the merchant's public key or info about a channel."""
        if deposit_txid is None:
            return jsonify({'public_key': self.server.discovery(),
                            'version': self.server.PROTOCOL_VERSION})
        else:
            try:
                return jsonify(self.server.status(deposit_txid))
            except PaymentChannelNotFoundError as e:
                raise NotFound(str(e))
            except Exception as e:
                raise BadRequest(str(e))

    def post(self):
        """Open a payment channel.

        Params (json):
            deposit_tx (string): serialized deposit transaction.
            redeem_script (string): serialized redeem script.

        Response (json) 2xx:
            deposit_txid (string): deposit transaction id.
        """
        try:
            # Validate parameters
            params = request.values.to_dict()
            if 'deposit_tx' not in params:
                raise BadParametersError('No deposit provided.')
            elif 'redeem_script' not in params:
                raise BadParametersError('No redeem script provided.')

            # Open the payment channel
            deposit_txid = self.server.open(params['deposit_tx'], params['redeem_script'])

            # Respond with the deposit transaction id as confirmation
            return jsonify({'deposit_txid': deposit_txid})
        except Exception as e:
            raise BadRequest(str(e))

    def put(self, deposit_txid):
        """Receive payments inside a payment channel.

        Args:
            deposit_txid (string): initial signed deposit transaction id.

        Params (json):
            payment_tx (string): half-signed serialized payment transaction.
        """
        try:
            # Validate parameters
            params = request.values.to_dict()
            if 'payment_tx' not in params:
                raise BadParametersError('No payment provided.')

            # Receive a new payment in the channel
            payment_txid = self.server.receive_payment(deposit_txid, params['payment_tx'])

            # Respond with the payment transaction id as confirmation
            return jsonify({'payment_txid': payment_txid})
        except PaymentChannelNotFoundError as e:
            raise NotFound(str(e))
        except Exception as e:
            raise BadRequest(str(e))

    def delete(self, deposit_txid):
        """Close a payment channel.

        Args:
            deposit_txid (string): initial signed deposit transaction id.

        Params (json):
            signature (string): deposit_txid signed by customer's private key.

        Response (json) 2xx:
            payment_txid (string): final payment channel transaction id.
        """
        try:
            # Validate parameters
            params = request.values.to_dict()
            if 'signature' not in params:
                raise BadParametersError('No signature provided.')

            # Close the payment channel
            payment_txid = self.server.close(deposit_txid, params['signature'])

            return jsonify({'payment_txid': payment_txid})
        except PaymentChannelNotFoundError as e:
            raise NotFound(str(e))
        except Exception as e:
            raise BadRequest(str(e))
