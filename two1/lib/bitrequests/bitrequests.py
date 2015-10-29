""""BitRequests, or requests with 402 ability.

BitTransfer Protocol:

An instant off chain approach to transfering Bitcoin.

Flow from clients perspective (user 1):

1. user 1 does a 21 mine
    - user 1 has 100k satohsi in earnings
2. user 1 does a 21 status
    - CLI displays earnings (aggregated shares) as their balance
3. User does a 21 buy endpoint/current-weather from user 2
    - Here user 1 does a call to user 2's server
        - user 2 responds with a 402 of their price / and their 21 username
    if user 1 decides to pay for that endpoint:
        - user 1 sends to user 2 the message (u1, pay, u2, price) (the transfer)
          signed with their private key (aka: machine auth)
            - user 2 sends this to the server
            - server checks if u1 has enough money to pay u2 (balance table).
                - if not, check earnings table.
                    - if earnings table, transfer from earnings -> balance.
            - server updates u2 & u1's balance to reflect the payment price.
            - server sends 200 OK to u2, who then sends data to u1 in 200
"""
import time
import json
import requests
import logging

logger = logging.getLogger('bitrequests')

class BitRequestsError(Exception):
    pass


class UnsupportedPaymentMethodError(BitRequestsError):
    pass


class ResourcePriceGreaterThanMaxPriceError(BitRequestsError):
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
            headers (dict): dict of headers with payment data to send to the
                API server to inform payment status for the resource.
        """
        raise NotImplementedError()

    def get_402_info(self, url):
        """Method for retrieving 402 metadata associated with the resource.

        Args:
            url (string): URL of the requested resource.

        Returns:
            headers (dict): dict of headers from the resource.
                Example: {'price': 5000, 'username': 'some_merchant'}
        """
        raise NotImplementedError()

    def request(self, method, url, max_price=None, **kwargs):
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
            response (requests.response): successful response from paying for
                the requested resource.
        """
        # Make the initial request for the resource
        response = requests.request(method, url, **kwargs)

        # Return if we receive a status code other than 402: payment required
        if (response.status_code != requests.codes.payment_required):
            return response

        # Pass the response to the main method for handling payment
        logger.debug('[BitRequests] 402 payment required: {} satoshi.'.format(
            response.headers['price']))
        payment_headers = self.make_402_payment(response, max_price)

        # Add any user-provided headers to the payment headers dict
        if 'headers' in kwargs:
            if isinstance(kwargs['headers'], dict):
                kwargs['headers'].update(payment_headers)
            else:
                raise ValueError('argument \'headers\' must be a dict.')
        else:
            kwargs['headers'] = payment_headers

        # Complete the original resource request
        paid_response = requests.request(method, url, **kwargs)

        # Log success or failure of the operation
        if paid_response.status_code == requests.codes.ok:
            logger.debug('[BitRequests] Successfully purchased resource.')
        else:
            if 'detail' in paid_response.text:
                raise ValueError(paid_response.json()["detail"])
            logger.debug('[BitRequests] Could not purchase resource.')

        # Add the amount that was paid as an attribute to the response object
        setattr(paid_response, 'amount_paid', int(response.headers['price']))

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

    def __init__(self, wallet, username):
        """Initialize the bittransfer with wallet and username."""
        super().__init__()
        self.wallet = wallet
        self.username = username

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

        # Verify resource cost against our budget
        if max_price and price > max_price:
            max_price_err = 'Resource price ({}) exceeds max price ({}).'
            raise ResourcePriceGreaterThanMaxPriceError(max_price_err.format(price, max_price))

        # Create and sign BitTranfer
        bittransfer = json.dumps({
            'payer': self.username,
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
        price = headers.get(BitTransferRequests.HTTP_BITCOIN_PRICE)
        payee_address = headers.get(BitTransferRequests.HTTP_BITCOIN_ADDRESS)
        payee_username = headers.get(BitTransferRequests.HTTP_BITCOIN_USERNAME)
        return {BitTransferRequests.HTTP_BITCOIN_PRICE: int(price),
                BitTransferRequests.HTTP_BITCOIN_ADDRESS: payee_address,
                BitTransferRequests.HTTP_BITCOIN_USERNAME: payee_username}


class OnChainRequests(BitRequests):

    """BitRequests for making on-chain payments."""

    HTTP_BITCOIN_PRICE = 'price'
    HTTP_BITCOIN_ADDRESS = 'bitcoin-address'

    def __init__(self, wallet):
        """Initialize the on-chain request with a wallet."""
        super().__init__()
        self.wallet = wallet

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
            'Return-Wallet-Address': return_address
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

    HTTP_BITCOIN_PRICE = 'price'
    HTTP_BITCOIN_MICROPAYMENT_SERVER = 'bitcoin-micropayment-server'
    HTTP_BITCOIN_MICROPAYMENT_TOKEN = 'bitcoin-micropayment-token'

    DEFAULT_DEPOSIT_AMOUNT = 100000
    DEFAULT_DURATION = 86400
    DEFAULT_CLOSE_AMOUNT = 1000

    def __init__(self, wallet, deposit_amount=DEFAULT_DEPOSIT_AMOUNT, duration=DEFAULT_DURATION, close_amount=DEFAULT_CLOSE_AMOUNT):
        """Initialize the channel requests with a payment channel client."""
        super().__init__()
        from two1.lib.channels import PaymentChannelClient
        self._channelclient = PaymentChannelClient(wallet)
        self._deposit_amount = deposit_amount
        self._duration = duration
        self._close_amount = close_amount

    def make_402_payment(self, response, max_price):
        """Make a channel payment."""

        # Retrieve payment headers
        price = response.headers.get(ChannelRequests.HTTP_BITCOIN_PRICE)
        server_url = response.headers.get(ChannelRequests.HTTP_BITCOIN_MICROPAYMENT_SERVER)

        # Verify that the payment method is supported
        if price is None or server_url is None:
            raise UnsupportedPaymentMethodError(
                'Resource does not support channels payment method.')

        # Convert string headers into correct data types
        price = int(price)

        # Verify resource cost against our budget
        if max_price and price > max_price:
            max_price_err = 'Resource price ({}) exceeds max price ({}).'
            raise ValueError(max_price_err.format(price, max_price))

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
            elif status.ready and (status.balance - price) < self._close_amount:
                logger.debug("[ChannelRequests] Channel balance low. Refreshing channel.")
                self._channelclient.close(channel_url)
                status = self._channelclient.status(channel_url)
                logger.debug("[ChannelRequests] Channel spend txid is {}".format(status.spend_txid))
                channel_url = None

        # Open a new channel if we don't have a usable one
        if not channel_url or not status.ready:
            logger.debug("[ChannelRequests] Opening channel at {} with deposit {}.".format(channel_url, self._deposit_amount))
            channel_url = self._channelclient.open(server_url, self._deposit_amount, self._duration, zeroconf=True, use_unconfirmed=True)
            status = self._channelclient.status(channel_url)
            logger.debug("[ChannelRequests] Channel deposit txid is {}".format(status.deposit_txid))

        # Pay through the channel
        logger.debug("[ChannelRequests] Paying channel {} with amount {}.".format(channel_url, price))
        token = self._channelclient.pay(channel_url, price)

        return {ChannelRequests.HTTP_BITCOIN_MICROPAYMENT_TOKEN: token}

    def get_402_info(self, url):
        """Get channel payment information about the resource."""
        response = requests.get(url)
        price = response.headers.get(ChannelRequests.HTTP_BITCOIN_PRICE)
        channel_url = response.headers.get(ChannelRequests.HTTP_BITCOIN_MICROPAYMENT_SERVER)
        return {ChannelRequests.HTTP_BITCOIN_PRICE: price,
                ChannelRequests.HTTP_BITCOIN_MICROPAYMENT_SERVER: channel_url}
