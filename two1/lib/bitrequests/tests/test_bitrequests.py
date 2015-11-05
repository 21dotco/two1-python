import json
import pytest
import requests
from two1.commands.config import Config
from two1.lib.bitrequests import BitTransferRequests
from two1.lib.bitrequests import OnChainRequests
from two1.lib.bitrequests import BitRequestsError
from two1.lib.bitrequests import BitRequests


class MockRequest:
    text = ""


class MockWallet:

    """Mock Wallet for testing BitRequests."""

    ADDR = 'test_21_user_address'
    TXID = 'test_txid'
    TXN = 'test_transaction_hex'

    @property
    def current_address(self):
        """Mock current user wallet address."""
        return MockWallet.ADDR

    def make_signed_transaction_for(self, address, amount, use_unconfirmed):
        """Mock ability to sign a transaction to an address."""
        signed_tx = {'txid': MockWallet.TXID, 'txn': MockWallet.TXN}
        return [signed_tx]


class MockBitRequests(BitRequests):
    def make_402_payment(self, response, max_price):
        return {'Bitcoin-Transaction': 'paid'}


def mockrequest(*args, **kwargs):
    mock_request = MockRequest()
    setattr(mock_request, 'status_code', 402)
    setattr(mock_request, 'headers', {'price': '1337'})
    setattr(mock_request, 'response_method', args[0])
    return mock_request


##############################################################################

# Set up Two1 command line config
config = Config()
# Inject the mock wallet into config as a test dependency
wallet = MockWallet()


def test_onchain_request():
    """Test that it handles on-chain requests."""
    bit_req = OnChainRequests(wallet)
    test_max_price = 10000
    price = 1000
    address = 'test_bitserv_host_address'
    mock_request = MockRequest()
    headers = {'price': price, 'bitcoin-address': address}
    setattr(mock_request, 'headers', headers)

    # Test that we can make a successful 402 payment
    onchain_pmt = bit_req.make_402_payment(mock_request, test_max_price)
    assert type(onchain_pmt) == dict
    assert onchain_pmt['Bitcoin-Transaction'] == MockWallet.TXN
    assert onchain_pmt['Return-Wallet-Address'] == MockWallet.ADDR

    # Test that an error is raised if the server doesn't support onchain
    with pytest.raises(BitRequestsError):
        headers = {'price': price}
        setattr(mock_request, 'headers', headers)
        bit_req.make_402_payment(mock_request, test_max_price)


def test_bittransfer_request():
    """Test that it handles bit-transfer requests."""
    bit_req = BitTransferRequests(config.machine_auth, config.username)
    test_max_price = 10000
    price = 1000
    address = 'test_bitserv_host_address'
    user = 'test_username'
    mock_request = MockRequest()
    headers = {'price': price, 'bitcoin-address': address, 'username': user}
    url = 'http://localhost:8000/weather/current-temperature?place=94102'
    setattr(mock_request, 'headers', headers)
    setattr(mock_request, 'url', url)

    # Test that we can make a successful 402 payment
    bittransfer_pmt = bit_req.make_402_payment(mock_request, test_max_price)
    assert type(bittransfer_pmt) == dict
    bit_transfer = json.loads(bittransfer_pmt['Bitcoin-Transfer'])
    assert bit_transfer['payee_address'] == address
    assert bit_transfer['payee_username'] == user
    assert bit_transfer['amount'] == price
    assert bit_transfer['description'] == url

    # Test that an error is raised if the server doesn't support bittransfers
    with pytest.raises(BitRequestsError):
        headers = {'price': price}
        setattr(mock_request, 'headers', headers)
        bit_req.make_402_payment(mock_request, test_max_price)


def test_bitrequest_kwargs():
    """Test that it correctly forwards keyword arguments."""
    url_streamable_data = 'http://httpbin.org/stream-bytes/1000'
    bit_req = MockBitRequests()

    # Test we fail when trying to stream bytes by default
    res = bit_req.request('get', url_streamable_data)
    assert res.status_code == 200
    assert res.raw.read() == b''

    # Test that we can successfully use a keyword argument to stream bytes
    res = bit_req.request('get', url_streamable_data, stream=True)
    assert res.status_code == 200
    assert res.raw.read() != b''
    assert res.headers['transfer-encoding'] == 'chunked'


def test_bitrequest_amount(monkeypatch):
    # Patch requests from making actual http requests
    monkeypatch.setattr(requests, 'request', mockrequest)
    bit_req = MockBitRequests()

    # Test that the response object contains and amount paid attribute
    res = bit_req.request('get', 'fakeurl')
    assert res.amount_paid == 1337


def test_bitrequest_custom_headers(monkeypatch):
    # Patch requests from making actual http requests
    monkeypatch.setattr(requests, 'request', mockrequest)
    bit_req = MockBitRequests()

    # Test that the request can have custom headers
    headers = {'Content-Type': 'application/json'}
    res = bit_req.request('get', 'fakeurl', headers=headers)
    assert res.status_code == 402

    # Test for error response when improper headers are provided
    headers = 'bad-headers'
    with pytest.raises(ValueError):
        res = bit_req.request('get', 'fakeurl', headers=headers)


def test_bitrequest_methods(monkeypatch):
    # Patch requests from making actual http requests
    monkeypatch.setattr(requests, 'request', mockrequest)
    bit_req = MockBitRequests()

    # Test that convenience methods are run as the correct methods
    res = bit_req.get('fakeurl')
    assert res.response_method == 'get'
    res = bit_req.put('fakeurl')
    assert res.response_method == 'put'
    res = bit_req.post('fakeurl')
    assert res.response_method == 'post'
    res = bit_req.delete('fakeurl')
    assert res.response_method == 'delete'
    res = bit_req.head('fakeurl')
    assert res.response_method == 'head'
