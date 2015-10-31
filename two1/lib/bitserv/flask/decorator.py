"""Flask bitserv payment library for selling 402 API endpoints."""
from urllib.parse import urlparse
from functools import wraps
from flask import jsonify, request
from flask.views import MethodView
from werkzeug.exceptions import HTTPException, BadRequest

from two1.lib.wallet import Wallet
from two1.lib.bitcoin import Transaction
from two1.lib.bitcoin.utils import bytes_to_str

from ..payment_methods import OnChain, PaymentChannel, BitTransfer
from ..payment_server import PaymentServer


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

    def __init__(self, app, wallet, allowed_methods=None):
        """Configure bitserv settings.

        Args:
            app (flask.Flask): A flask app to wrap payment handling around.
            wallet (two1.lib.wallet.Wallet): The merchant's wallet instance.
        """
        if allowed_methods is None:
            self.allowed_methods = [
                PaymentChannel(*flask_channel_adapter(app, PaymentServer(wallet))),
                OnChain(wallet),
                BitTransfer(wallet)]

    def required(self, price, **kwargs):
        """API route decorator to request payment for a resource.

        This function stores the resource price in a closure. It will verify
        the validity of a payment, and allow access to the resource if the
        payment is successfully accepted.
        """
        def decorator(fn):
            @wraps(fn)
            def _fn(*fn_args, **fn_kwargs):
                # Calculate resource cost
                nonlocal price
                _price = price(request) if callable(price) else price
                # Need better way to pass server url to payment methods (FIXME)
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


def flask_channel_adapter(app, server):
    """Initialize the Flask views with RESTful access to the Channel."""
    pmt_view = Channel.as_view('channel', server)
    app.add_url_rule('/payment', defaults={'deposit_txid': None},
                     view_func=pmt_view, methods=('GET',))
    app.add_url_rule('/payment', view_func=pmt_view, methods=('POST',))
    app.add_url_rule('/payment/<deposit_txid>', view_func=pmt_view,
                     methods=('GET', 'PUT', 'DELETE'))
    return server, '/payment'


class Channel(MethodView):

    def __init__(self, server):
        """Initialize the channel view with a PaymentServer object."""
        self.server = server

    def get(self, deposit_txid):
        """Return the merchant's public key or info about a channel."""
        if deposit_txid is None:
            return jsonify({'public_key': self.server.discovery()})
        else:
            try:
                return jsonify(self.server.status(deposit_txid))
            except Exception as e:
                raise BadRequest(str(e))

    def post(self):
        """Initialize the payment channel handshake.

        Params (query):
            refund_tx (string): half-signed serialized refund transaction

        Response (json) 2xx:
            refund_tx (string): fully-signed serialized refund transaction
        """
        try:
            params = request.values.to_dict()
            # Validate parameters
            if 'refund_tx' not in params:
                raise BadParametersError('No refund provided.')

            # Initialize the payment channel
            refund_tx = Transaction.from_hex(params['refund_tx'])
            self.server.initialize_handshake(refund_tx)

            # Respond with the fully-signed refund transaction
            success = {'refund_tx': bytes_to_str(bytes(refund_tx))}
            return jsonify(success)
        except Exception as e:
            # Catch payment exceptions and send error response to client
            raise BadRequest(str(e))

    def put(self, deposit_txid):
        """Complete the payment channel handshake or receive payments.

        Args:
            deposit_txid (string): initial signed deposit transaction id

        Params (json) (one of the following):
            deposit_tx (string): half-signed serialized deposit transaction
            payment_tx (string):  half-signed serialized payment transaction
        """
        try:
            params = request.values.to_dict()
            if 'deposit_tx' in params:
                # Complete the handshake using the received deposit
                deposit_tx = Transaction.from_hex(params['deposit_tx'])
                self.server.complete_handshake(deposit_txid, deposit_tx)
                return jsonify()
            elif 'payment_tx' in params:
                # Receive a payment in the channel using the received payment
                payment_tx = Transaction.from_hex(params['payment_tx'])
                self.server.receive_payment(deposit_txid, payment_tx)
                return jsonify({'payment_txid': str(payment_tx.hash)})
            else:
                raise KeyError('No deposit or payment received.')
        except Exception as e:
            raise BadRequest(str(e))

    def delete(self, deposit_txid):
        """Close a payment channel.

        Args:
            deposit_txid (string): initial signed deposit transaction id

        Response (json) 2xx:
            payment_txid (string): final payment channel transaction id
        """
        try:
            payment_txid = self.server.close(deposit_txid)
            return jsonify({'payment_txid': payment_txid})
        except Exception as e:
            raise BadRequest(str(e))
