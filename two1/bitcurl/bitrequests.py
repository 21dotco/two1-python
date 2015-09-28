""""BitRequests, or requests with 402 ability."""

import json
import requests


class BitRequests(object):

    """Summary.

    Attributes:
        DEF_PAYMENT_REQUIRED_STATUS_CODE (int): Description
    """

    DEF_PAYMENT_REQUIRED_STATUS_CODE = 402
    DEF_HEADERS = {'content-type': 'application/json'}

    @classmethod
    def get(cls, url, wallet, **kwargs):
        """Summary.

        Returns:
            TYPE: Description

        Args:
            url (TYPE): Description
            wallet (TYPE): Description
            **kwargs: Description
        """
        return cls._get(cls, url, wallet, **kwargs)

    @classmethod
    def post(cls, url, wallet, **kwargs):
        """Summary.

        Returns:
            TYPE: Description

        Args:
            url (TYPE): Description
            wallet (TYPE): Description
            **kwargs: Description
        """
        return cls._post(cls, url, wallet, **kwargs)

    def __init__(self):
        """Summary.

        Args:
            arg (TYPE): Description
        """
        self.wallet = None
        self.data = None

    def _handle_response(self, request):
        """Handle all responses for BitRequests.

        If status codes are not in spec, then 
        return the request object. 

        Args:
            request (request): 

        Returns:
            TYPE: Description
        """
        print("got request obeject: {}".format(request))
        if request.status_code == self.DEF_PAYMENT_REQUIRED_STATUS_CODE:
            self._pay_endpoint(self, request)
        else:
            return request

    def _pay_endpoint(self, request):
        """Summary.

        Args:
            request (TYPE): Description

        Returns:
            TYPE: Description
        """
        # get the price from the headers, in satoshis
        price = int(request.headers.get("price"))
        # get the payout address from the headers
        address_to_pay = request.headers.get("bitcoin-address")
        # use wallet to make a tranasction for the recipient
        signed_tx = self.wallet.make_signed_transaction_for(
            address_to_pay, price)
        # returns a list of transactions, since we are just paying
        # one party, take the first element, and the tx_id from it
        txid = signed_tx[0].get("txid")
        txn = signed_tx[0].get("txn")
        print("txid: {}".format(txid))
        print("txn: {}".format(txn))
        # insert the raw tranasction into the headers
        bitcoin_headers = {"Bitcoin-Transaction": txn}
        # pay the endpoint again
        print("paying the endpoint: \
             address_to_pay {}, price {}".format(
            address_to_pay, price
            )
        )
        self._post(
            self,
            request.url,
            self.wallet,
            data=self.data,
            headers=bitcoin_headers
        )

    def _get(self, url, wallet, **kwargs):
        """Summary.

        Args:
            url (TYPE): Description
            **kwargs: Description

        Returns:
            TYPE: Description
        """
        self.wallet = wallet
        response = requests.get(url, **kwargs)
        return self._handle_response(response)

    def _post(self, url, wallet, **kwargs):
        """Summary.

        Args:
            url (TYPE): Description
            wallet (TYPE): Description
            **kwargs: Description

        Returns:
            TYPE: Description
        """
        self.wallet = wallet
        self.data = kwargs.get("data")
        # if there are no default headers
        # set them. 402 server 
        # is very specific about json
        if "headers" not in kwargs:
            kwargs["headers"] = {}
        # update the dictionary with standard headers
        kwargs["headers"].update(self.DEF_HEADERS)
        # post the response to the server
        response = requests.post(url, **kwargs)
        return self._handle_response(self, response)

if __name__ == "__main__":
    """
    namespace bitrequests such that it's imported a la
    requests.
    https://github.com/kennethreitz/requests/blob/master/requests/__init__.py#L15

    example usage of requests:
    >>> import requests
    >>> r = requests.get('https://www.python.org')
    >>> r.status_code
    200
    """
    from two1.config import Config
    config = Config()
    bitrequests = BitRequests
    req = bitrequests.post(
        "http://djangobitcoin-devel-e0ble.herokuapp.com/phone/send-sms",
        config.wallet,
        data=json.dumps(
            {
                'phone': '4124809904',
                'text': 'Looking forward to seeing you tomorrow in the Command Line Center to continue the hackathon'
            }
        )
    )
