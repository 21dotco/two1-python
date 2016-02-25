"""Mock objects for testing."""
import json
import codecs
import collections

import two1.lib.bitcoin as bitcoin
import two1.lib.channels as channels


class MockTwo1Wallet:

    """Mock Two1 Wallet."""

    PRIVATE_KEY = bitcoin.PrivateKey.from_int(0x70b5d984b8a8e072e201ddd59ff3deb2d7303467136001c062ffa23552ea058e)
    BALANCE = 123000

    def __init__(self):
        """Returns a new MockTwo1Wallet object."""
        self._balance = MockTwo1Wallet.BALANCE

    def sign_message(self, message, account_name_or_index=None, key_index=0):
        """Sign an arbitrary message."""
        return codecs.encode(bytes(self.PRIVATE_KEY.sign(message)), 'base64_codec').decode()

    def get_message_signing_public_key(self):
        """Return a mock public key for signing messages."""
        return self.PRIVATE_KEY.public_key

    def confirmed_balance(self):
        """Return the wallet's confirmed balance in satoshis."""
        return self.BALANCE

    def unconfirmed_balance(self):
        """Return the wallet's unconfirmed balance in satoshis."""
        return self._balance

    def pay(self, amount):
        """Make a payment."""
        self._balance = self._balance - amount


class MockBitResponse:

    """Mock response from a BitRequests request."""

    SUCCESS_RESPONSE = 'You bought something with bitcoin!'
    FAILURE_RESPONSE = 'Method not supported!'
    GET_COST = 5000
    POST_COST = 20000

    def __init__(self, method='get', data=None, headers={}):
        """Return a new MockBitResponse object."""
        if method.upper() == 'GET':
            self.status_code = 200
            self.amount_paid = self.GET_COST
            self.text = self.SUCCESS_RESPONSE
        elif method.upper() == 'POST':
            self.status_code = 201
            self.amount_paid = self.POST_COST
            self.text = json.dumps(data)
        else:
            self.status_code = 405
            self.text = self.FAILURE_RESPONSE


class MockBitRequests:

    """Mock BitRequests behavior."""

    HEADERS = {'Bitcoin-Address': '1ExZSz3NsfEqKXnFrg5cJ8F3UTRzcnZ8J7', 'Price': MockBitResponse.GET_COST}

    def __init__(self, wallet, username=None):
        """Return a new MockBitRequests object."""
        self.wallet = wallet
        self.username = username

    def get_402_info(self, resource):
        """Mock 402-related headers."""
        return MockBitRequests.HEADERS

    def request(self, method, url, max_price=None, **kwargs):
        """Mock a paid 402 request."""
        self.method = method
        self.url = url
        self.max_price = max_price
        any(setattr(self, key, val) for key, val in kwargs.items())
        self.response = MockBitResponse(self.method, self.data, self.headers)
        if hasattr(self.wallet, 'pay') and hasattr(self.response, 'amount_paid'):
            self.wallet.pay(self.response.amount_paid)
        elif hasattr(self.response, 'amount_paid'):
            self.wallet.wallet.pay(self.response.amount_paid)
        return self.response


class MockTwentyOneRestClient:

    """Mock TwentyOneRestClient behavior."""

    FLUSHED = 240000

    def __init__(self, server_url, machine_auth, username=None):
        """Return a new MockTwentyOneRestClient object."""
        self.server_url = server_url
        self.machine_auth = machine_auth
        self.username = username
        self._earnings = self.machine_auth.wallet.BALANCE
        self._flushed = MockTwentyOneRestClient.FLUSHED

    def get_earnings(self):
        """Get net earnings."""
        return dict(total_earnings=self.machine_auth.wallet.unconfirmed_balance(), flushed_amount=self._flushed)


class MockChannelClient:

    """Mock ChannelClient behavior."""

    Channel = collections.namedtuple('Channel', ['balance', 'state'])
    URL = 'test://fake'
    BALANCE = 99000

    def __init__(self):
        """Return a new MockChannelClient object."""
        self.channels = {}
        self.channels[MockChannelClient.URL] = MockChannelClient.Channel(MockChannelClient.BALANCE, channels.PaymentChannelState.READY)

    def sync(self):
        """Mocks the channel `sync` method."""
        pass

    def list(self):
        """Mocks the channel `list` method."""
        return self.channels.keys()

    def status(self, url):
        """Mocks the channel `list` method."""
        return self.channels[url]


class MockConfig:

    """Mock Config behavior."""

    collect_analytics = False

    def __init__(self):
        """Return a new MockConfig object."""
        self.username = 'MockTestUser'
        self.purchases = []

    def log_purchase(self, **kwargs):
        """Mock purchase log."""
        self.purchases.append(kwargs)
