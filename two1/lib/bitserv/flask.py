"""Flask bitserv payment library for selling 402 API endpoints."""
from functools import wraps
from flask import jsonify, request
from flask.views import MethodView
from werkzeug.exceptions import HTTPException, BadRequest

from two1.lib.wallet import Wallet
from two1.lib.bitcoin import Transaction
from two1.lib.bitcoin.utils import bytes_to_str

from .payment_methods import OnChain, PaymentChannel
from .payment_server import PaymentServer


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
                 default_micro_server='payment'):
        """Configure bitserv settings.

        Args:
            app (flask.Flask): a flask app to wrap payment handling around.
        """
        self.default_price = default_price
        self.default_address = default_address
        self.default_micro_server = default_micro_server
        self.allowed_methods = [
            PaymentChannel(app, FlaskProcessor, db), OnChain(db)]

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
                micro_server_path = (micro_server or self.default_micro_server)
                for method in self.allowed_methods:
                    payment_headers.update(method.get_402_headers(
                        price=price or self.default_price,
                        micro_server=request.url_root + micro_server_path,
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


class FlaskProcessor:

    def __init__(self, app, db=None):
        """Initialize the Flask views with RESTful access to the Channel."""
        self.wallet = Wallet()
        self.server = PaymentServer(self.wallet, db)
        pmt_view = Channel.as_view('channel', self.server)
        app.add_url_rule('/payment', defaults={'deposit_txid': None},
                         view_func=pmt_view, methods=('GET',))
        app.add_url_rule('/payment', view_func=pmt_view, methods=('POST',))
        app.add_url_rule('/payment/<deposit_txid>', view_func=pmt_view,
                         methods=('GET', 'PUT', 'DELETE'))


class Channel(MethodView):

    def __init__(self, server):
        self.server = server

    def get(self, deposit_txid):
        if deposit_txid is None:
            return jsonify({'public_key': self.server.discovery()})
        else:
            try:
                return jsonify(self.server.status(deposit_txid))
            except Exception as e:
                raise BadRequest(str(e))

    def post(self):
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
            return BadRequest(str(e))

    def delete(self, deposit_txid):
        try:
            payment_txid = self.server.close(deposit_txid)
            return jsonify({'payment_txid': payment_txid})
        except Exception as e:
            return BadRequest(str(e))
