""""BitRequests, or requests with 402 ability."""
import json
import requests
from urllib.parse import urlsplit


class BitRequests(object):

    """Bitcoin enabled requests.

    Implements the 402 bitcoin payment
    protocol on the client side.

    If a payment is to come back as a 402,
    requests are handled, and paid in the
    proper fasion until success or failure
    sent back from a bitcoin enabled server.

    An example of a bitcoin enabled api server can
    be seen in two1.git, under two1/examples

    Example Usage:

    bitrequests.post(
        "http://bitcoinapiserver.com/api/",
        config,
        data=json.dumps({"data":True})
    )

    Attributes:
        data (JSON): payload to send to server (JSON)
        DEF_HEADERS (dict): http headers sent to enforce json
        DEF_PAYMENT_REQUIRED_STATUS_CODE (int): the 402 http code
        paid_amount (int): amount of btc paid, once transaction has
        been sent out, in satoshis
        config (config): a config object from two1.
    """

    DEF_INSUFFICIENT_FUNDS_MESSAGE = 'Insufficient Funds'
    DEF_INVALID_TOKEN_MESSAGE = 'Invalid BitcoinToken'
    DEF_PAYMENT_REQUIRED_STATUS_CODE = 402
    DEF_TOKEN_ENDPOINT = "bitcoin_auth/token"
    DEF_HEADERS = {'content-type': 'application/json'}

    @staticmethod
    def get_base_url(url):
        """Derive baseurl from url."""
        return "{0.scheme}://{0.netloc}/".format(urlsplit(url))

    @classmethod
    def get(cls, url, config, **kwargs):
        """Passthrough into BitRequests's _get.

        Returns:
            request (request) : a bitcoin request call

        Args:
            url (str): endpoint to send request
            config (config): a config object from two1.
            **kwargs: additional payload for requests
        """
        return cls._get(cls, url, config, **kwargs)

    @classmethod
    def post(cls, url, config, **kwargs):
        """Passthrough into BitRequests _post.

        Returns:
            request (request) : a bitcoin request call

        Args:
            url (str): endpoint to send request
            config (config): a config object from two1.
            **kwargs: additional payload for requests
        """
        return cls._post(cls, url, config, **kwargs)

    def __init__(self):
        """An API into bitcoin enabled requests."""
        self.config = None
        self.data = None
        self.files = None
        self.paid_amount = None

    def _handle_response(self, request):
        """Handle all responses for BitRequests.

        If status codes are not in spec, then
        return the request object.

        Args:
            request (request): request object

        Returns:
            request (request): request object

        Raises:
            ValueError: error if request is not ok
        """
        print("got request object: {}, body: {}".format(request, request.text))
        if request.status_code == self.DEF_PAYMENT_REQUIRED_STATUS_CODE:
            # before we pay the endpoint, check to see if we've recieved
            # an auth message particular to bitcointoken usage
            if self._check_bitcoin_token_message(self, request):
                return self._refresh_bitcoin_token(self, request)
            else:
                return self._pay_endpoint(self, request)
        elif request.ok:
            # if request is okay, we've paid
            # and the 402 handshake was successfull
            # add a paid_amount to the object.
            setattr(
                request,
                'paid_amount',
                self.paid_amount if hasattr(self, 'paid_amount') else 0
            )
            if "BitcoinToken" in request.text:
                self._write_bitcoin_token(
                    self,
                    request.json()['BitcoinToken']
                )
            return request
        else:
            raise ValueError(request)

    def _check_bitcoin_token_message(self, request):
        """Check to see if the 402 text refers to token authentication."""
        return self.DEF_INSUFFICIENT_FUNDS_MESSAGE in request.text \
            or self.DEF_INVALID_TOKEN_MESSAGE in request.text

    def _refresh_bitcoin_token(self, request):
        """Buy another BitcoinToken from server & continue original call.

        Args:
            request (request): request object

        Returns:
            request: call back to the original call.
        """
        # clear bitcoin file
        self._wipe_bitcoin_token(self)
        # buy another one
        self._get(
            self,
            self.get_base_url(request.url) + self.DEF_TOKEN_ENDPOINT,
            self.config
        )
        # perform original call again
        request_method = self._get
        extra_request_args = {}
        if 'post' in request.headers['allow'].lower():
            extra_request_args['data'] = self.data
            request_method = self._post
        return request_method(
            self,
            request.url,
            self.config,
            **extra_request_args
        )

    def _pay_endpoint(self, request):
        """Pay the endpoint using your wallet.

        Checks if wallet balance is greater
        than the cost of the endpoint call itself.
        If so, create a signed transaction for the recipient
        and construct a payment request (to the same endpoint)
        with the signed_tx in the header.

        Args:
            request (request): request object

        Returns:
            request (request): request object from a post with
            a Bitcoin-Transaction in the HTTP headers.
        """
        # get the price from the headers, in satoshis
        price = int(request.headers.get("price"))
        # check if we have the funds to pay for this
        # request
        if price > self.config.wallet.balance():
            raise ValueError("Insufficient funds to purchase endpoint")
        # get the payout address from the headers
        address_to_pay = request.headers.get("bitcoin-address")
        # use wallet to make a tranasction for the recipient
        signed_tx = self.config.wallet.make_signed_transaction_for(
            address_to_pay, price, use_unconfirmed=True)
        # returns a list of transactions, since we are just paying
        # one party, take the first element, and the tx_id from it
        txid = signed_tx[0].get("txid")
        txn = signed_tx[0].get("txn")
        print("txid: {}".format(txid))
        print("txn: {}".format(txn))
        # insert the raw tranasction and current address into the headers
        bitcoin_headers = {
            "Bitcoin-Transaction": txn,
            "Return-Wallet-Address": self.config.wallet.current_address
        }
        # pay the endpoint again
        print("paying the endpoint: \
             address_to_pay {}, price {}".format(
            address_to_pay, price
        )
        )
        # record how much we paid for this
        # call
        self.paid_amount = price
        # prep the request with bitcoin headers
        # for a 402 call
        extra_request_args = {'headers': bitcoin_headers}
        # the default payment request method
        request_method = self._get
        # if we're posting, switch method to post
        # and append additional information to
        # extra_request_args, such as the data
        if 'post' in request.headers['allow'].lower():
            extra_request_args['data'] = self.data

            if self.files:
                # We may have read the whole file if this is the second time
                # we send it (first time we were asked to pay). So we must
                # seek back to the beginning.
                for file_tuple in self.files.values():
                    if len(file_tuple) == 2:  # tuple: (file_name, file_obj)
                        file_tuple[1].seek(0)
                extra_request_args['files'] = self.files

            request_method = self._post
        return request_method(
            self,
            request.url,
            self.config,
            **extra_request_args
        )

    def _write_bitcoin_token(self, bitcointoken):
        """Write bitcointoken to config."""
        self.config.update_key("bitcointoken", bitcointoken)
        self.config.save()

    def _wipe_bitcoin_token(self):
        """Wipe bitcointoken from config."""
        self.config.update_key("bitcointoken", None)
        self.config.save()

    def _check_for_bitcoin_token(self):
        """Insert bitcoin token into headers if exists."""
        if 'bitcointoken' in self.config.defaults:
            self.DEF_HEADERS.update(
                {'bitcoin-token': self.config.bitcointoken}
            )

    def _get(self, url, config, **kwargs):
        """Perform a bitcoin enabled GET request.

        Args:
            url (str): endpoint to send request
            config (config): a config object from two1.
            **kwargs: additional payload for requests

        Returns:
            request (request) : a bitcoin request call
        """
        self.config = config
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        self._check_for_bitcoin_token(self)
        kwargs["headers"].update(self.DEF_HEADERS)
        response = requests.get(url, **kwargs)
        return self._handle_response(self, response)

    def _post(self, url, config, **kwargs):
        """Perform a bitcoin enabled POST request.

        Args:
            url (str): endpoint to send request
            config (config): a config object from two1.
            **kwargs: additional payload for requests

        Returns:
            request (request) : a bitcoin request call
        """
        self.config = config
        self.data = kwargs.get("data")
        self.files = kwargs.get("files")
        # if there are no default headers
        # set them. 402 server
        # is very specific about json
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        # update the dictionary with standard headers (only if there is data)
        if self.data:
            kwargs["headers"].update(self.DEF_HEADERS)
        # post the response to the server
        response = requests.post(url, **kwargs)
        return self._handle_response(self, response)

if __name__ == "__main__":
    """
    Namespace bitrequests such that it's imported a la requests.
    https://github.com/kennethreitz/requests/blob/master/requests/__init__.py#L15

    example usage of requests:
    >>> import requests
    >>> r = requests.get('https://www.python.org')
    >>> r.status_code
    200
    """
    from commands.config import Config
    config = Config()
    bitrequests = BitRequests
    req = bitrequests.post(
        "http://djangobitcoin-devel-e0ble.herokuapp.com/phone/send-sms",
        config,
        data=json.dumps(
            {
                'phone': '4124809904',
                'text': 'Hey! How are ya?'
            }
        )
    )
