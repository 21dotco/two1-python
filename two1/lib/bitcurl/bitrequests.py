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


class BitRequests(object):

    """Bitcoin enabled requests.

    Implements the 402 bitcoin payment
    protocol on the client side.

    If a payment is to come back as a 402,
    requests are handled, and paid in the
    proper fasion until success or failure
    sent back from a bitcoin enabled server.

    An example of a bitcoin enabled api server can
    be seen in two1.git, under two1/examples.
    """

    def __init__(self, config, payment_method="bittransfer"):
        """Initialize BitRequests.

        Args:
            config (two1.commands.config): a two1 config object
            payment_method (str, optional): payment method for 402
                fufillment.
        """
        self.config = config
        self.machine_auth = self.config.machine_auth
        self.payment_method = payment_method
        self.data = None
        self.files = None

    def _handle_response(self, response):
        """Handle a response from a 402 enabled server.

        Args:
            response (request): request object

        Returns:
            response (request): request object

        Raises:
            ValueError: if conditions are not met.
        """
        print(response, response.text)
        if requests.status_codes._codes[response.status_code][0] == \
                'payment_required' and "Payment Required" in response.text:
            return self._pay_endpoint(response)
        elif response.ok:
            return response
        else:
            raise ValueError(response.text)

    def _get_payment_info_from_headers(self, headers):
        """Get payment information from headers.

        This can include:
            Bitcoin-Address
            Price
            Username (bittransfer)

        Args:
            headers (TYPE): Description

        Returns:
            (payment info tuple): Payment information
                in a tuple format
        """
        return (
            headers.get("bitcoin-address"),
            int(headers.get("price")),
            headers.get("username")
        )

    def _create_and_sign_bittransfer(self, payer, payee_address, payee_username,
                                   amount, description):
        """Create and sign a bitcoin transfer

        Args:
            payer (TYPE): Description
            payee_address (TYPE): Description
            payee_username (TYPE): Description
            amount (TYPE): Description
            description (TYPE): Description

        Returns:
            TYPE: Description
        """
        bittransfer = json.dumps(
            {
                "payer": payer,
                "payee_address": payee_address,
                "payee_username": payee_username,
                "amount": amount,
                "description": description
            }
        )
        signature = self.machine_auth.sign_message(
            bittransfer
        )
        return bittransfer, signature

    def _create_and_sign_transaction(self, payee_address, amount,
                                     use_unconfirmed=True):
        """Create and sign a raw bitcoin transaction

        Args:
            payee_address (str): Address to pay.
            amount (int): Satoshis to pay.
            use_unconfirmed (bool, optional): use zero conf funds.

        Returns:
            txn: Raw bitcoin trasnaction

        Raises:
            ValueError: If wallet is not solvent.
        """
        # ensure that we have sufficient funds for this
        # payment.
        if amount > self.config.wallet.balance():
            raise ValueError("Insufficient funds to create transaction")
        # use wallet to make a tranasction for the recipient
        signed_tx = self.config.wallet.make_signed_transaction_for(
            payee_address, amount, use_unconfirmed=use_unconfirmed
        )
        txid = signed_tx[0].get("txid")
        txn = signed_tx[0].get("txn")
        print("txid: {}\ntxn: {}".format(txid, txn))
        return txn

    def _pay_endpoint(self, response):
        """From a response (request object),
        pay the path inside of it via a BitTransfer.

        Args:
            response (request): request object

        Returns:
            response (request): request object
        """
        payee_address, price, payee_username = \
            self._get_payment_info_from_headers(response.headers)
        # construct payment args for the response.
        request_args = {'headers': {}}
        if self.payment_method == "bittransfer":
            bittransfer, signature = self._create_and_sign_bittransfer(
                    self.config.username,
                    payee_address,
                    payee_username,
                    price,
                    response.url
                )
            request_args['headers']['Bitcoin-Transfer'] = bittransfer
            request_args['headers']['Authorization'] = signature
        if self.payment_method == "onchain":
            request_args["headers"]["Bitcoin-Transaction"] = \
                self._create_and_sign_transaction(
                    payee_address, price, True
                )
            request_args["headers"]["Return-Wallet-Address"] = \
                self.config.wallet.current_address
        # determine request to make
        request_method = self.get
        # attach POST data if it exists
        if self.data:
            request_method = self.post
            request_args['data'] = self.data
        # attach file data if it exists
        if self.files:
            # We may have read the whole file if this is the second time
            # we send it (first time we were asked to pay). So we must
            # seek back to the beginning.
            for file_tuple in self.files.values():
                if len(file_tuple) == 2:  # tuple: (file_name, file_obj)
                    file_tuple[1].seek(0)
            request_args['files'] = self.files
        return request_method(
            response.url,
            **request_args
        )

    def get(self, url, **kwargs):
        """Send a get request to a 402 enabled server.

        Args:
            url (str): endpoint to send request
            **kwargs: additional payload for requests

        Returns:
            response (request): a requests resposne
        """
        response = requests.get(url, **kwargs)
        return self._handle_response(response)

    def post(self, url, **kwargs):
        """Send a post request to a 402 enabled server.

        Args:
            url (str): endpoint to send request
            **kwargs: additional payload for requests

        Returns:
            response (request): a requests resposne
        """
        if 'data' in kwargs:
            self.data = kwargs['data']
        if 'files' in kwargs:
            self.files = kwargs['files']
        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs["headers"].update(
            {'content-type': 'application/json'}
        )
        response = requests.post(url, **kwargs)
        return self._handle_response(response)

if __name__ == "__main__":
    from two1.commands.config import Config
    c = Config()
    bc = BitRequests(c, "onchain")
    bc.get("http://localhost:8000/weather/current-temperature?place=94103")
