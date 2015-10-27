"""Server routes for processing payments out of band from API calls."""
from flask import jsonify, request
from flask.views import MethodView
from werkzeug.exceptions import BadRequest
from two1.lib.wallet.two1_wallet import Two1Wallet
from two1.lib.wallet.two1_wallet import Two1WalletProxy
from .paymentserver import PaymentServer


class ProcessorBase:
    pass


class FlaskProcessor(ProcessorBase):

    def __init__(self, app, db=None):
        self.wallet = Two1WalletProxy(Two1Wallet.DEFAULT_WALLET_PATH)
        self.server = PaymentServer(self.wallet, db)
        uri = '/payment'
        channel = '/<deposit_txid>'
        app.add_url_rule(uri, view_func=Handshake.as_view('handshake'))
        app.add_url_rule(uri + channel, view_func=Channel.as_view('channel'))


class Handshake(MethodView):

    def get(self):
        return jsonify({'public_key': self.server.discovery()})

    def post(self):
        params = request.get_json()
        try:
            # Validate parameters
            if 'refund_tx' not in params:
                raise BadParametersError('No refund provided.')

            # Initialize the payment channel
            refund_tx = PCUtil.parse_tx(params['refund_tx'])
            self.server.initialize_handshake(refund_tx)

            # Respond with the fully-signed refund transaction
            success = {'refund_tx': PCUtil.serialize_tx(refund_tx)}
            return Response(success)
        except Exception as e:
            # Catch payment exceptions and send error response to client
            raise BadRequest(str(e))


class Channel(MethodView):

    def get(self, deposit_txid):
        try:
            params = request.get_json()
            info = params('deposit_txid')
            return Response(info)
        except Exception as e:
            raise BadRequest(str(e))

    def put(self, deposit_txid):
        try:
            params = request.get_json()
            if 'deposit_tx' in params:
                # Complete the handshake using the received deposit
                deposit_tx = Transaction.from_hex(params['deposit_tx'])
                self.server.complete_handshake(deposit_txid, deposit_tx)
                return Response()
            elif 'payment_tx' in params:
                # Receive a payment in the channel using the received payment
                payment_tx = Transaction.from_hex(params['payment_tx'])
                self.server.receive_payment(deposit_txid, payment_tx)
                return Response({'payment_txid': str(payment_tx.hash)})
            else:
                raise KeyError('No deposit or payment received.')
        except Exception as e:
            return BadRequest(str(e))

    def delete(self, deposit_txid):
        try:
            payment_txid = self.server.close(deposit_txid)
            return Response({'payment_txid': payment_txid})
        except Exception as e:
            return BadRequest(str(e))
