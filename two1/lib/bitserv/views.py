"""Server routes for processing payments out of band from API calls."""
from flask import jsonify, request
from flask.views import MethodView
from werkzeug.exceptions import BadRequest

from two1.lib.bitcoin.txn import Transaction
from two1.lib.bitcoin.utils import bytes_to_str
from two1.lib.wallet.two1_wallet import Wallet

from .paymentserver import PaymentServer

wallet = Wallet()


class FlaskProcessor:

    def __init__(self, app, db=None):
        """Initialize the Flask views with RESTful access to the Channel."""
        self.server = PaymentServer(wallet, db)
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
