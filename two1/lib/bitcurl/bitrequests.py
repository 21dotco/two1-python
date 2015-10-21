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
import json
import requests


class BitRequestsError(Exception):
    pass


class UnsupportedPaymentMethodError(BitRequestsError):
    pass


class BitRequests(object):

    """Implements the HTTP 402 bitcoin payment protocol on the client side.

    If an initial request returns '402: Payment Required', the class defers to
    its `make_402_payment()` to create the necessary payment.
    """

    HTTP_BITCOIN_PRICE = 'price'
    HTTP_BITCOIN_ADDRESS = 'bitcoin-address'

    def __init__(self, config):
        """Initialize BitRequests.

        Args:
            config (two1.commands.config): a two1 config object
        """
        self.config = config

    def make_402_payment(self, headers, max_price):
        """Payment handling method implemented by a BitRequests subclass.

        Args:
            response (requests.response): 402 response from the API server.
            max_price (int): maximum allowed price for a request (in satoshi).

        Returns:
            headers (dict): dict of headers with payment data to send to the
                API server to inform payment status for the resource.
        """
        raise NotImplementedError()

    def request(self, method, url, data=None, max_price=None):
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
        response = requests.request(method, url, data=data)

        # Return if we receive a status code other than 402: payment required
        if response.status_code != requests.codes.payment_required:
            return response

        # Pass the response to the main method for handling payment
        payment_headers = self.make_402_payment(response, max_price)

        # Complete the response and return with a requests.response object
        paid_response = requests.request(
            method, url, data=data, headers=payment_headers)

        return paid_response


class BitTransferRequests(BitRequests):

    """BitRequests for making bit-transfer payments."""

    HTTP_BITCOIN_USERNAME = 'username'

    def __init__(self, config):
        """Initialize the bit-transfer with keyring machine auth."""
        super().__init__(config)
        self.machine_auth = MachineAuth.from_keyring()

    def make_402_payment(self, response, max_price):
        """Make a bit-transfer payment to the payment-handling service."""
        # Retrieve payment headers
        headers = response.headers
        price = headers.get(BitRequests.HTTP_BITCOIN_PRICE)
        payee_address = headers.get(BitRequests.HTTP_BITCOIN_ADDRESS)
        payee_username = headers.get(BitTransferRequests.HTTP_BITCOIN_USERNAME)

        # Verify that the payment method is supported
        if price is None or payee_address is None or payee_username is None:
            raise UnsupportedPaymentMethodError(
                'Resource does not support that payment method.')

        # Convert string headers into correct data types
        price = int(price)

        # Create and sign BitTranfer
        bittransfer = json.dumps({
            'payer': self.config.username,
            'payee_address': payee_address,
            'payee_username': payee_username,
            'amount': price,
            'description': response.url
        })
        signature = self.machine_auth.sign_message(bittransfer).decode()

        return {
            'Bitcoin-Transfer': bittransfer,
            'Authorization': signature
        }


class OnChainRequests(BitRequests):

    """BitRequests for making on-chain payments."""

    def __init__(self, config):
        """Initialize the on-chain request with keyring machine auth."""
        super().__init__(config)
        self.machine_auth = MachineAuth.from_keyring()

    def make_402_payment(self, response, max_price):
        """Make an on-chain payment."""
        # Retrieve payment headers
        headers = response.headers
        price = headers.get(BitRequests.HTTP_BITCOIN_PRICE)
        payee_address = headers.get(BitRequests.HTTP_BITCOIN_ADDRESS)

        # Verify that the payment method is supported
        if price is None or payee_address is None:
            raise UnsupportedPaymentMethodError(
                'Resource does not support that payment method.')

        # Convert string headers into correct data types
        price = int(price)

        # Create the signed transaction
        onchain_payment = self.config.wallet.make_signed_transaction_for(
            payee_address, price, use_unconfirmed=True)[0].get('txn')
        return_address = self.config.wallet.current_address

        return {
            'Bitcoin-Transaction': onchain_payment,
            'Return-Wallet-Address': return_address
        }
