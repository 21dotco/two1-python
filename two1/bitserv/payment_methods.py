"""This module contains methods for making paid HTTP requests to 402-enabled servers."""
import json
import logging
import requests
import threading

import two1
from two1.bitcoin.txn import Transaction
from two1.blockchain.twentyone_provider import TwentyOneProvider
from .models import OnChainSQLite3

logger = logging.getLogger('bitserv')


class PaymentError(Exception):
    """Generic error for exceptions encountered during payment validation."""
    pass


class InsufficientPaymentError(PaymentError):
    """Raised when the amount paid is less than the payment required."""
    pass


class InvalidPaymentParameterError(PaymentError):
    """Raised when an incorrect or malformed payment parameter is provided."""
    pass


class DuplicatePaymentError(PaymentError):
    """Raised when attempting to re-use a payment token to purchase a resource."""
    pass


class TransactionBroadcastError(PaymentError):
    """Raised when broadcasting a transaction to the bitcoin network fails."""
    pass


class PaymentBelowDustLimitError(PaymentError):
    """Raised when the paid amount is less than the bitcoin network dust limit."""
    pass


class ServerError(Exception):
    """Raised when an error is received from a remote server on a request."""
    pass


class PaymentBase:

    """Base class for payment methods."""

    def should_redeem(self, request_headers):
        """Method for checking if we should use a derived payment method."""
        return all(h in request_headers.keys() for h in self.payment_headers)

    @property
    def payment_headers(self):
        """Derived list of headers to use for payment processing.

        Returns:
            (list):
                List of required headers that a client should present
                in order to redeem a payment of this method.
                Example: ['Bitcoin-Transaction']
        """
        raise NotImplementedError()

    def get_402_headers(self, price, **kwargs):
        """Derived dict of headers to return in the initial 402 response.

        Args:
            price: Endpoint price in satoshis
        Returns:
            (dict):
                Dict of headers that the server uses to inform the client
                how to remit payment for the resource.
                Example: {'address': '1MDxJYsp4q4P46RiigaGzrdyi3dsNWCTaR', 'price': 500}
        """
        raise NotImplementedError()

    def redeem_payment(self, price, request_headers, payment_headers):
        """Derived method for processing and validating payment.

        Args:
            request_headers (dict): Headers sent by client with their request.
            payment_headers (dict): Required headers to verify the client's
                request against.
        Returns:
            (boolean): Whether or not the payment is valid.
        Raises:
            InsufficientPaymentError: Payment received does not match the
                resource's price.
            InvalidPaymentParameterError: Payment was made to an address other
                than the merchant's provided address.
            DuplicatePaymentError: Payment has already been used to pay for a
                resource from the merchant.
        """
        raise NotImplementedError()


###############################################################################


class OnChain(PaymentBase):

    """Making a payment on the bitcoin blockchain."""

    lock = threading.Lock()
    http_payment_data = 'Bitcoin-Transaction'
    http_402_price = 'Price'
    http_402_address = 'Bitcoin-Address'
    DUST_LIMIT = 3000  # dust limit in satoshi

    def __init__(self, wallet, db=None, db_dir=None):
        """Initialize payment handling for on-chain payments."""
        self.db = db or OnChainSQLite3(db_dir=db_dir)
        self.address = wallet.get_payout_address()
        self.provider = TwentyOneProvider(two1.TWO1_PROVIDER_HOST)

    @property
    def payment_headers(self):
        """List of headers to use for payment processing."""
        return [OnChain.http_payment_data]

    def get_402_headers(self, price, **kwargs):
        """Dict of headers to return in the initial 402 response."""
        return {OnChain.http_402_price: price,
                OnChain.http_402_address: kwargs.get('address', self.address)}

    def redeem_payment(self, price, request_headers, **kwargs):
        """Validate the transaction and broadcast it to the blockchain."""
        raw_tx = request_headers[OnChain.http_payment_data]
        logger.debug('[BitServ] Receieved transaction: {}'.format(raw_tx))

        # verify txn is above dust limit
        if price < OnChain.DUST_LIMIT:
            raise PaymentBelowDustLimitError(
                'Payment amount is below dust limit ({} Satoshi)'.format(OnChain.DUST_LIMIT))

        try:
            payment_tx = Transaction.from_hex(raw_tx)
        except:
            raise InvalidPaymentParameterError('Invalid transaction hex.')

        # Find the output with the merchant's address
        payment_index = payment_tx.output_index_for_address(kwargs.get('address', self.address))
        if payment_index is None:
            raise InvalidPaymentParameterError('Not paid to merchant.')

        # Verify that the payment is made for the correct amount
        if payment_tx.outputs[payment_index].value != price:
            raise InsufficientPaymentError('Incorrect payment amount.')

        # Synchronize the next block of code to manage its atomicity
        with self.lock:
            # Verify that we haven't seen this transaction before
            if self.db.lookup(str(payment_tx.hash)):
                raise DuplicatePaymentError('Payment already used.')
            else:
                self.db.create(str(payment_tx.hash), price)

            try:
                # Broadcast payment to network
                txid = self.provider.broadcast_transaction(raw_tx)
                logger.debug('[BitServ] Broadcasted: ' + txid)
            except Exception as e:
                # Roll back the database entry if the broadcast fails
                self.db.delete(str(payment_tx.hash))
                raise TransactionBroadcastError(str(e))

        return True


class PaymentChannel(PaymentBase):

    """Making a payment within a payment channel."""

    http_payment_token = 'Bitcoin-Payment-Channel-Token'
    http_402_price = 'Price'
    http_402_micro_server = 'Bitcoin-Payment-Channel-Server'

    def __init__(self, server, endpoint_path):
        """Initialize payment handling for on-chain payments."""
        self.server = server
        self.endpoint_path = endpoint_path

    @property
    def payment_headers(self):
        """List of headers to use for payment processing."""
        return [PaymentChannel.http_payment_token]

    def get_402_headers(self, price, **kwargs):
        """Dict of headers to return in the initial 402 response."""
        return {PaymentChannel.http_402_price: price,
                PaymentChannel.http_402_micro_server: kwargs['server_url'] + self.endpoint_path}

    def redeem_payment(self, price, request_headers, **kwargs):
        """Validate the micropayment and redeem it."""
        txid = request_headers[PaymentChannel.http_payment_token]
        try:
            # Redeem the transaction in its payment channel
            paid_amount = self.server.redeem(txid)
            # Verify the amount of the payment against the resource price
            return paid_amount >= int(price)
        except Exception as e:
            raise e


class BitTransfer(PaymentBase):

    """Making a payment via 21 BitTransfer protocol."""

    http_payment_data = 'Bitcoin-Transfer'
    http_402_price = 'Price'
    http_402_address = 'Bitcoin-Address'
    http_authorization = 'Authorization'
    http_402_username = 'Username'

    verification_url = two1.TWO1_HOST + '/pool/account/{}/bittransfer/'
    account_file = two1.TWO1_CONFIG_FILE

    def __init__(self, wallet, verification_url=None, username=None, seller_account=None):
        """Initialize payment handling for on-chain payments."""
        self.address = wallet.get_payout_address()
        self.verification_url = verification_url or BitTransfer.verification_url

        if username:
            self.seller_username = username
        else:
            acct = seller_account or BitTransfer.account_file
            with open(acct, 'r') as f:
                account = json.loads(f.read())
            seller = account['username']
            self.seller_username = seller

    @property
    def payment_headers(self):
        """List of headers to use for payment processing."""
        return [BitTransfer.http_payment_data, BitTransfer.http_authorization]

    def get_402_headers(self, price, **kwargs):
        """Dict of headers to return in the initial 402 response."""
        return {BitTransfer.http_402_price: price,
                BitTransfer.http_402_address: self.address,
                BitTransfer.http_402_username: self.seller_username}

    def redeem_payment(self, price, request_headers, **kwargs):
        """Verify that the BitTransfer is valid.

            (1) Check that amount sent in transfer
                is correct
            (2) Authenticate & verify via 3rd party
                (21.co) server.
        """
        # extract bittransfer & sig from headers
        bittransfer = request_headers[BitTransfer.http_payment_data]
        signature = request_headers[BitTransfer.http_authorization]

        # check amount in transfer
        resource_price = price
        if not json.loads(bittransfer)['amount'] == resource_price:
            raise InsufficientPaymentError('Incorrect payment amount.')

        # now verify with 21.co server that transfer is valid
        try:
            verification_response = requests.post(
                self.verification_url.format(
                    self.seller_username
                ),
                data=json.dumps({
                    'bittransfer': bittransfer,
                    'signature': signature
                }),
                headers={'content-type': 'application/json'}
            )
            if verification_response.ok:
                return True
        except requests.ConnectionError:
            logger.debug('[BitServ] Client failed to connect to server.')

        # handle verification server bad response
        try:
            error = verification_response.json()['error']
        except (ValueError, KeyError):
            raise ServerError(verification_response.content)
        else:
            raise PaymentError(error)
