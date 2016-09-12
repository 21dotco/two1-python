"""This module provides various BitRequests methods, including:
`BitTransferRequests`, `OnChainRequests`, and `ChannelRequests`. These objects
can be used to make 402-enabled, paid HTTP requests to servers that
support the 402-protocol and those specific payment methods.
"""
import time
import json
import codecs
import logging
import requests
import urllib.parse

import two1
from two1.commands.util import config
import two1.commands.util.exceptions as exceptions

logger = logging.getLogger('bitrequests')


class BitRequestsError(Exception):
    """Generic exception for BitRequests modules."""
    pass


class UnsupportedPaymentMethodError(BitRequestsError):
    """Raised when using a payment method that is not supported by a server."""
    pass


class ResourcePriceGreaterThanMaxPriceError(BitRequestsError):
    """Raised when paying for a resource whose price exceeds the client's maximum allowable price."""
    pass


class InsufficientBalanceError(BitRequestsError):
    """Raised when attempting to pay for a resource which has a price that exceedes the available balance."""
    pass


class BitRequests(object):

    """Implements the HTTP 402 bitcoin payment protocol on the client side.

    If an initial request returns '402: Payment Required', the class defers to
    its `make_402_payment()` to create the necessary payment.
    """

    def __init__(self):
        """Initialize BitRequests."""
        pass

    def make_402_payment(self, response, max_price):
        """Payment handling method implemented by a BitRequests subclass.

        Args:
            response (requests.response): 402 response from the API server.
            max_price (int): maximum allowed price for a request (in satoshi).

        Returns:
            headers (dict):
                dict of headers with payment data to send to the
                API server to inform payment status for the resource.
        """
        raise NotImplementedError()

    def get_402_info(self, url):
        """Method for retrieving 402 metadata associated with the resource.

        Args:
            url (string): URL of the requested resource.

        Returns:
            headers (dict):
                dict of headers from the resource.
                Example: {'price': 5000, 'username': 'some_merchant'}
        """
        raise NotImplementedError()

    def _reset_file_positions(self, files, data):
        """Resets the `read` cursor position of a group of files.

        This method will mutate all file-like objects in the `files` or `data`
        parameters. It has no effect when `file` and `data` are None, or when
        `data` is not a file type.

        Args:
            data (file): a file-like object.
            files (dict or list): a key-value store of file identifiers and
                file-like objects or tuples that contain file-like objects.

        TODO: allow for `files` lists where there may be multiple values for
            the same key, which currently collide when cast to a dict
        """
        if files:
            file_list = list(dict(files).values())
            # Allow for one level of nesting for file fields
            if isinstance(file_list[0], (list, tuple)):
                file_list = [f[1] for f in file_list]
        elif data:
            file_list = [data]
        else:
            return

        # Only seek through the objects if they are seekable
        for f in file_list:
            if hasattr(f, 'seek'):
                f.seek(0)

    def request(self, method, url, max_price=None, mock_requests=False, **kwargs):
        """Make a 402 request for a resource.

        This is the BitRequests public method that should be used to complete a
        402 request using the desired payment method (as constructed by a class
        implementing BitRequests)

        Args:
            method (string): HTTP method for completing the request in lower-
                case letters. Examples: 'get', 'post', 'put'
            url (string): URL of the requested resource.
            data (dict): python dict of parameters to send with the request.
            max_price (int): maximum allowed price for a request (in satoshi).

        Returns:
            response (requests.response):
                response from paying for the requested resource.
        """
        if mock_requests:
            fake_response = requests.models.Response()
            fake_response.status_code = 200
            fake_response._content = b''
            return fake_response

        # Make the initial request for the resource
        response = requests.request(method, url, **kwargs)

        # Return if we receive a status code other than 402: payment required
        if response.status_code != requests.codes.payment_required:
            return response

        # Pass the response to the main method for handling payment
        logger.debug('[BitRequests] 402 payment required: {} satoshi.'.format(
            response.headers['price']))
        payment_headers = self.make_402_payment(response, max_price)

        # Reset the position of any files that have been used
        self._reset_file_positions(kwargs.get('files'), kwargs.get('data'))

        # Add any user-provided headers to the payment headers dict
        if 'headers' in kwargs:
            if isinstance(kwargs['headers'], dict):
                kwargs['headers'].update(payment_headers)
            else:
                raise ValueError('argument \'headers\' must be a dict.')
        else:
            kwargs['headers'] = payment_headers

        paid_response = requests.request(method, url, **kwargs)
        setattr(paid_response, 'amount_paid', int(response.headers['price']))

        if paid_response.status_code == requests.codes.ok:
            logger.debug('[BitRequests] Successfully purchased resource.')
        else:
            logger.debug('[BitRequests] Could not purchase resource.')

        return paid_response

    def get(self, url, max_price=None, **kwargs):
        """Make a paid GET request for a resource."""
        return self.request('get', url, max_price, **kwargs)

    def put(self, url, max_price=None, **kwargs):
        """Make a paid PUT request for a resource."""
        return self.request('put', url, max_price, **kwargs)

    def post(self, url, max_price=None, **kwargs):
        """Make a paid POST request for a resource."""
        return self.request('post', url, max_price, **kwargs)

    def delete(self, url, max_price=None, **kwargs):
        """Make a paid DELETE request for a resource."""
        return self.request('delete', url, max_price, **kwargs)

    def head(self, url, max_price=None, **kwargs):
        """Make a paid HEAD request for a resource."""
        return self.request('head', url, max_price, **kwargs)


class BitTransferRequests(BitRequests):

    """BitRequests for making bit-transfer payments."""

    HTTP_BITCOIN_PRICE = 'price'
    HTTP_BITCOIN_ADDRESS = 'bitcoin-address'
    HTTP_BITCOIN_USERNAME = 'username'

    def __init__(self, wallet, username=None, client=None):
        """Initialize the bittransfer with wallet and username."""
        from two1.server.machine_auth_wallet import MachineAuthWallet
        from two1.server import rest_client
        super().__init__()
        if isinstance(wallet, MachineAuthWallet):
            self.wallet = wallet
        else:
            self.wallet = MachineAuthWallet(wallet)
        if username is None:
            self.username = config.Config().username
        else:
            self.username = username
        if client is None:
            self.client = rest_client.TwentyOneRestClient(
                two1.TWO1_HOST, self.wallet, self.username)
        else:
            self.client = client

    def make_402_payment(self, response, max_price):
        """Make a bit-transfer payment to the payment-handling service."""
        # Retrieve payment headers
        headers = response.headers
        price = headers.get(BitTransferRequests.HTTP_BITCOIN_PRICE)
        payee_address = headers.get(BitTransferRequests.HTTP_BITCOIN_ADDRESS)
        payee_username = headers.get(BitTransferRequests.HTTP_BITCOIN_USERNAME)

        # Verify that the payment method is supported
        if price is None or payee_address is None or payee_username is None:
            raise UnsupportedPaymentMethodError(
                'Resource does not support that payment method.')

        # Convert string headers into correct data types
        price = int(price)

        # verify that we have the money to purchase the resource
        buffer_balance = self.client.get_earnings()["total_earnings"]
        if price > buffer_balance:
            insuff_funds_err = 'Resource price ({}) exceeds buffer balance ({}).'
            raise InsufficientBalanceError(insuff_funds_err.format(price, buffer_balance))

        # Verify resource cost against our budget
        if max_price and price > max_price:
            max_price_err = 'Resource price ({}) exceeds max price ({}).'
            raise ResourcePriceGreaterThanMaxPriceError(max_price_err.format(price, max_price))

        # Get the signing public key
        pubkey = self.wallet.get_public_key()
        compressed_pubkey = codecs.encode(pubkey.compressed_bytes, 'base64').decode()

        # Create and sign BitTranfer
        bittransfer = json.dumps({
            'payer': self.username,
            'payer_pubkey': compressed_pubkey,
            'payee_address': payee_address,
            'payee_username': payee_username,
            'amount': price,
            'timestamp': time.time(),
            'description': response.url
        })
        if not isinstance(bittransfer, str):
            raise TypeError("Serialized bittransfer must be a string")
        signature = self.wallet.sign_message(bittransfer)
        logger.debug('[BitTransferRequests] Signature: {}'.format(signature))
        logger.debug('[BitTransferRequests] BitTransfer: {}'.format(bittransfer))
        return {
            'Bitcoin-Transfer': bittransfer,
            'Authorization': signature
        }

    def get_402_info(self, url):
        """Get bit-transfer payment information about the resource."""
        headers = requests.get(url).headers
        price = headers.get(BitTransferRequests.HTTP_BITCOIN_PRICE, 0)
        payee_address = headers.get(BitTransferRequests.HTTP_BITCOIN_ADDRESS)
        payee_username = headers.get(BitTransferRequests.HTTP_BITCOIN_USERNAME)
        return {BitTransferRequests.HTTP_BITCOIN_PRICE: int(price),
                BitTransferRequests.HTTP_BITCOIN_ADDRESS: payee_address,
                BitTransferRequests.HTTP_BITCOIN_USERNAME: payee_username}


class OnChainRequests(BitRequests):

    """BitRequests for making on-chain payments."""

    HTTP_BITCOIN_PRICE = 'price'
    HTTP_BITCOIN_ADDRESS = 'bitcoin-address'
    HTTP_PAYER_21USERNAME = 'Payer-21Username'

    def __init__(self, wallet):
        """Initialize the on-chain request with a wallet."""
        super().__init__()
        self.wallet = wallet
        try:
            self.username = config.Config().username
        except exceptions.FileDecodeError:
            self.username = None

    def make_402_payment(self, response, max_price):
        """Make an on-chain payment."""
        # Retrieve payment headers
        headers = response.headers
        price = headers.get(OnChainRequests.HTTP_BITCOIN_PRICE)
        payee_address = headers.get(OnChainRequests.HTTP_BITCOIN_ADDRESS)

        # Verify that the payment method is supported
        if price is None or payee_address is None:
            raise UnsupportedPaymentMethodError(
                'Resource does not support that payment method.')

        # Convert string headers into correct data types
        price = int(price)

        # Verify resource cost against our budget
        if max_price and price > max_price:
            max_price_err = 'Resource price ({}) exceeds max price ({}).'
            raise ResourcePriceGreaterThanMaxPriceError(max_price_err.format(price, max_price))

        # Create the signed transaction
        onchain_payment = self.wallet.make_signed_transaction_for(
            payee_address, price, use_unconfirmed=True)[0].get('txn').to_hex()
        return_address = self.wallet.current_address
        logger.debug('[OnChainRequests] Signed transaction: {}'.format(
            onchain_payment))

        return {
            'Bitcoin-Transaction': onchain_payment,
            'Return-Wallet-Address': return_address,
            OnChainRequests.HTTP_BITCOIN_PRICE: str(price),
            OnChainRequests.HTTP_PAYER_21USERNAME: urllib.parse.quote(self.username) if self.username else None
        }

    def get_402_info(self, url):
        """Get on-chain payment information about the resource."""
        headers = requests.get(url).headers
        price = headers.get(OnChainRequests.HTTP_BITCOIN_PRICE)
        payee_address = headers.get(OnChainRequests.HTTP_BITCOIN_ADDRESS)
        return {OnChainRequests.HTTP_BITCOIN_PRICE: int(price),
                OnChainRequests.HTTP_BITCOIN_ADDRESS: payee_address}


class ChannelRequests(BitRequests):
    """BitRequests for making channel payments."""

    import two1.channels as channels  # noqa

    HTTP_BITCOIN_PRICE = 'price'
    HTTP_BITCOIN_PAYMENT_CHANNEL_SERVER = 'bitcoin-payment-channel-server'
    HTTP_BITCOIN_PAYMENT_CHANNEL_TOKEN = 'bitcoin-payment-channel-token'
    HTTP_PAYER_21USERNAME = 'Payer-21Username'

    DEFAULT_DEPOSIT_AMOUNT = 100000
    DEFAULT_DURATION = 86400
    DEFAULT_ZEROCONF = True
    DEFAULT_USE_UNCONFIRMED = False

    def __init__(self, wallet, deposit_amount=DEFAULT_DEPOSIT_AMOUNT, duration=DEFAULT_DURATION):
        """Initialize the channel requests with a payment channel client."""
        super().__init__()
        self._channelclient = ChannelRequests.channels.PaymentChannelClient(wallet)
        self._deposit_amount = deposit_amount
        self._duration = duration
        try:
            self.username = config.Config().username
        except exceptions.FileDecodeError:
            self.username = None

    def make_402_payment(self, response, max_price):
        """Make a channel payment."""

        # Retrieve payment headers
        price = response.headers.get(ChannelRequests.HTTP_BITCOIN_PRICE)
        server_url = response.headers.get(ChannelRequests.HTTP_BITCOIN_PAYMENT_CHANNEL_SERVER)

        # Verify that the payment method is supported
        if price is None or server_url is None:
            raise UnsupportedPaymentMethodError(
                'Resource does not support channels payment method.')

        # Convert string headers into correct data types
        price = int(price)

        # Verify resource cost against our budget
        if max_price and price > max_price:
            max_price_err = 'Resource price ({}) exceeds max price ({}).'
            raise ResourcePriceGreaterThanMaxPriceError(max_price_err.format(price, max_price))

        # Look up channel
        channel_urls = self._channelclient.list(server_url)
        channel_url = channel_urls[0] if channel_urls else None

        if channel_url:
            # Get channel status
            status = self._channelclient.status(channel_url)

            # Check if channel has expired
            if status.ready and status.expired:
                logger.debug("[ChannelRequests] Channel expired. Refreshing channel.")
                self._channelclient.sync(channel_url)
                channel_url = None

            # Check if the channel balance is sufficient
            elif status.ready and status.balance < price:
                logger.debug("[ChannelRequests] Channel balance low. Refreshing channel.")
                self._channelclient.close(channel_url)
                status = self._channelclient.status(channel_url)
                logger.debug("[ChannelRequests] Channel spend txid is {}".format(status.spend_txid))
                channel_url = None

            # Check if the channel deposit is still being confirmed
            elif status.state == ChannelRequests.channels.PaymentChannelState.CONFIRMING_DEPOSIT:
                logger.debug("[ChannelRequests] Channel deposit tx still being confirmed.")
                self._channelclient.sync(channel_url)
                status = self._channelclient.status(channel_url)
                if not status.ready:
                    raise ChannelRequests.channels.NotReadyError("Channel not ready.")

        # Open a new channel if we don't have a usable one
        if not channel_url or not status.ready:
            logger.debug("[ChannelRequests] Opening channel at {} with deposit {}.".format(
                server_url, self._deposit_amount))
            channel_url = self._channelclient.open(
                server_url, self._deposit_amount, self._duration,
                zeroconf=ChannelRequests.DEFAULT_ZEROCONF, use_unconfirmed=ChannelRequests.DEFAULT_USE_UNCONFIRMED)
            status = self._channelclient.status(channel_url)
            logger.debug("[ChannelRequests] Channel deposit txid is {}".format(status.deposit_txid))

        # Pay through the channel
        logger.debug("[ChannelRequests] Paying channel {} with amount {}.".format(channel_url, price))
        try:
            token = self._channelclient.pay(channel_url, price)
        except ChannelRequests.channels.ClosedError:
            # If the server closed the channel, restart payment process to
            # negotiate a new channel.
            return self.make_402_payment(response, max_price)

        return {
            ChannelRequests.HTTP_BITCOIN_PAYMENT_CHANNEL_TOKEN: token,
            ChannelRequests.HTTP_BITCOIN_PRICE: str(price),
            ChannelRequests.HTTP_PAYER_21USERNAME: urllib.parse.quote(self.username) if self.username else None,
        }

    def get_402_info(self, url):
        """Get channel payment information about the resource."""
        response = requests.get(url)
        price = response.headers.get(ChannelRequests.HTTP_BITCOIN_PRICE)
        channel_url = response.headers.get(ChannelRequests.HTTP_BITCOIN_PAYMENT_CHANNEL_SERVER)
        return {ChannelRequests.HTTP_BITCOIN_PRICE: price,
                ChannelRequests.HTTP_BITCOIN_PAYMENT_CHANNEL_SERVER: channel_url}
