"""Mock objects for testing."""
import json
import codecs
import collections
import unittest.mock

import two1.bitcoin as bitcoin
import two1.channels as channels


class MockTwo1Wallet:

    """Mock Two1 Wallet."""

    PRIVATE_KEY = bitcoin.PrivateKey.from_int(0x70b5d984b8a8e072e201ddd59ff3deb2d7303467136001c062ffa23552ea058e)
    BALANCE = 123000

    def __init__(self, testnet=False):
        """Returns a new MockTwo1Wallet object."""
        self._balance = MockTwo1Wallet.BALANCE
        self.testnet = testnet

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

    def balances_by_address(self, account=0):
        """Return the wallet's balances by address."""
        return {self.current_address: {'confirmed': MockTwo1Wallet.BALANCE, 'total': MockTwo1Wallet.BALANCE}}

    @property
    def current_address(self):
        """Return the wallet's current address."""
        return self.PRIVATE_KEY.public_key.address()

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
            self.content = self.text = self.SUCCESS_RESPONSE
        elif method.upper() == 'POST':
            self.status_code = 201
            self.amount_paid = self.POST_COST
            self.content = self.text = json.dumps(data)
        else:
            self.status_code = 405
            self.content = self.text = self.FAILURE_RESPONSE

    def json(self):
        return json.loads(self.content)

    @property
    def ok(self):
        if 400 <= self.status_code < 600:
            return False
        return True


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


class MockHttpResponse:

    def __init__(self, data=None, status_code=200):
        self.data = data
        self.status_code = status_code
        if self.status_code == 200:
            self.ok = True

    def json(self):
        return json.loads(self.data)


class MockTwentyOneRestClient:

    """Mock TwentyOneRestClient behavior."""

    EARNINGS = 300000
    FLUSHED = 240000
    DEFAULT_VALUES = dict(
        get_earnings=dict(total_earnings=EARNINGS, flushed_amount=FLUSHED, total_payouts=1),
        flush_earnings=unittest.mock.DEFAULT,
        list_wallets=[dict(public_key="A6OwFY04TitVrO2fgUjbZ8sSMlei+EJlDizjukwdieqp",
                           payout_address="1NMM77kBVMydR7m1PpvwXoqANt7ikijVHw",
                           is_primary=True,
                           name="test_wallet")],
        login=unittest.mock.DEFAULT,
        get_mined_satoshis=[dict(date=1456768320, amount=10000, reason='CLI'),
                            dict(date=1456768327, amount=10000, reason='CLI')],
        get_notifications=dict(urgent_count=0, unread_count=0),
    )

    def __init__(self, server_url, machine_auth, username=None):
        """Return a new MockTwentyOneRestClient object."""
        self.server_url = server_url
        self.auth = machine_auth
        self.username = username

        # Create all mocks needed for introspection into method calls
        for method, default_value in MockTwentyOneRestClient.DEFAULT_VALUES.items():
            setattr(self, 'mock_' + method, unittest.mock.Mock(return_value=default_value))

    def get_earnings(self):
        return self.mock_get_earnings()

    def flush_earnings(self, amount, payout_address):
        return self.mock_flush_earnings()

    def login(self, payout_address, password):
        return self.mock_login(payout_address=payout_address, password=password)

    def get_mined_satoshis(self):
        return self.mock_get_mined_satoshis()

    def get_notifications(self, username, detailed=False):
        return self.mock_get_notifications(username, detailed)

    def list_wallets(self):
        return self.mock_list_wallets()


class MockChannelClient:

    """Mock ChannelClient behavior."""

    Channel = collections.namedtuple('Channel', ['balance', 'state', 'expiration_time'])
    URL = 'test://fake'
    BALANCE = 99000
    EXPIRATION = 1456962357

    def __init__(self, wallet):
        """Return a new MockChannelClient object."""
        self.wallet = wallet
        self.channels = {}
        self.channels[MockChannelClient.URL] = MockChannelClient.Channel(
            MockChannelClient.BALANCE, channels.PaymentChannelState.READY, MockChannelClient.EXPIRATION)

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
        self.mock_set = unittest.mock.Mock()
        self.mock_save = unittest.mock.Mock()

    def set(self, key, value):
        """Set a new config setting."""
        return self.mock_set(key, value)

    def save(self):
        """Save current settings."""
        return self.mock_save()

    def log_purchase(self, **kwargs):
        """Mock purchase log."""
        self.purchases.append(kwargs)
