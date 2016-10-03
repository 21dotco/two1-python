import io
import json
import unittest.mock as mock

import pytest
import requests

from two1.commands.util import config
from two1.bitrequests import BitTransferRequests
from two1.bitrequests import OnChainRequests
from two1.bitrequests import BitRequestsError
from two1.bitrequests import BitRequests


class MockWalletTxn:
    def to_hex(self):
        return 'test_transaction_hex'


class MockRequest:
    text = ""


class MockTwentyOneRestClient:
    def get_earnings(self):
        return {"total_earnings": 10000000}


class MockWallet:

    """Mock Wallet for testing BitRequests."""

    ADDR = 'test_21_user_address'
    TXID = 'test_txid'
    TXN = MockWalletTxn()

    @property
    def current_address(self):
        """Mock current user wallet address."""
        return MockWallet.ADDR

    def make_signed_transaction_for(self, address, amount, use_unconfirmed):
        """Mock ability to sign a transaction to an address."""
        signed_tx = {'txid': MockWallet.TXID, 'txn': MockWallet.TXN}
        return [signed_tx]

    def sign_message(self, message,
                     account_name_or_index=None,
                     key_index=0):
        """Mock sign message for bittransfer."""
        return "mock signed message"

    def get_message_signing_public_key(self):
        mock_pubkey = mock.Mock()
        mock_pubkey.compressed_bytes = b'test_21_pubkey'
        return mock_pubkey


class MockBitRequests(BitRequests):
    def make_402_payment(self, response, max_price):
        return {'Bitcoin-Transaction': 'paid'}


def mockrequest(*args, **kwargs):
    mock_request = MockRequest()
    mock_headers = {'price': '1337', 'bitcoin-address': '1THISISANADDRESS'}
    setattr(mock_request, 'status_code', 402)
    setattr(mock_request, 'headers', mock_headers)
    setattr(mock_request, 'response_method', args[0])
    return mock_request


##############################################################################

# Set up Two1 command line config
config = config.Config()
# Inject the mock wallet into config as a test dependency
wallet = MockWallet()
# Mock two1 rest client
client = MockTwentyOneRestClient()


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
    assert onchain_pmt['Bitcoin-Transaction'] == MockWallet.TXN.to_hex()
    assert onchain_pmt['Return-Wallet-Address'] == MockWallet.ADDR

    # Test that an error is raised if the server doesn't support onchain
    with pytest.raises(BitRequestsError):
        headers = {'price': price}
        setattr(mock_request, 'headers', headers)
        bit_req.make_402_payment(mock_request, test_max_price)


def test_bittransfer_request():
    """Test that it handles bit-transfer requests."""
    bit_req = BitTransferRequests(wallet, config.username, client)
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


def test_bittransfer_default_config():
    """Test that it looks up a username using the default Config."""
    current_username = config.username
    bit_req = BitTransferRequests(wallet)
    assert bit_req.username == current_username

    # Test that we can still use a custom username
    bit_req = BitTransferRequests(wallet, 'new_username')
    assert bit_req.username == 'new_username'


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


def test_get_402_info(monkeypatch):
    # Patch requests from making actual http requests
    monkeypatch.setattr(requests, 'get', mockrequest)

    # Test that OnChainRequests 402 info returns a dict of headers
    bit_req = OnChainRequests(wallet)
    headers = bit_req.get_402_info('fakeurl')
    assert type(headers) == dict
    assert headers['price'] == 1337
    assert headers['bitcoin-address'] == '1THISISANADDRESS'

    # Test that BitTransferRequests 402 info returns a dict of headers
    def mock_bittransfer_request(*args, **kwargs):
        mock_req = mockrequest(*args, **kwargs)
        mock_req.headers['username'] = 'long john silver'
        mock_req.headers['bitcoin-address'] = '3NEWADDRESS'
        return mock_req
    monkeypatch.setattr(requests, 'get', mock_bittransfer_request)
    bit_req = BitTransferRequests(wallet, config.username)
    headers = bit_req.get_402_info('fakeurl')
    assert type(headers) == dict
    assert headers['price'] == 1337
    assert headers['bitcoin-address'] == '3NEWADDRESS'
    assert headers['username'] == 'long john silver'


def test_post_files():
    """Tests that bitrequests successfully rewinds file streams in POSTs."""
    bit_req = MockBitRequests()

    # Test a full request with a `files` dict
    test_file = io.BytesIO(b'Test message.')
    with mock.patch('requests.request') as mock_request:
        # Clear the initial read buffer
        test_file.read()
        mock_request.return_value.status_code = 402
        assert test_file.read() == b''
        # Issue the request
        bit_req.post('http://upload_url', files=dict(file=test_file))
    assert mock_request.call_args_list[1][1]['files']['file'].read() == b'Test message.'

    # Test a full request with a file in the `data` body
    test_file = io.BytesIO(b'Another message.')
    with mock.patch('requests.request') as mock_request:
        # Clear the initial read buffer
        test_file.read()
        mock_request.return_value.status_code = 402
        assert test_file.read() == b''
        # Issue the request
        bit_req.post('http://upload_url', data=test_file)
    assert mock_request.call_args_list[1][1]['data'].read() == b'Another message.'


def test_reset_file_positions():
    """Unit test for the utility function to reset file positions."""
    bit_req = MockBitRequests()
    test_file_1 = io.BytesIO(b'First message.')
    test_file_2 = io.BytesIO(b'Second message.')

    # Test a dictionary of files
    file_dict = dict(file1=test_file_1, file2=test_file_2)
    test_file_1.read()
    test_file_2.read()
    assert test_file_1.read() == b''
    assert test_file_2.read() == b''
    bit_req._reset_file_positions(file_dict, None)
    assert test_file_1.read() == b'First message.'
    assert test_file_2.read() == b'Second message.'

    # Test a list of 2-tuples
    assert test_file_1.read() == b''
    assert test_file_2.read() == b''
    bit_req._reset_file_positions(file_dict, None)
    assert test_file_1.read() == b'First message.'
    assert test_file_2.read() == b'Second message.'

    # Test a list of 2-tuples with a nested tuple
    file_tuple = [('image1', ('firstfile.png', test_file_1, 'image/png')),
                  ('image2', ('secondfile.png', test_file_2, 'image/png'))]
    assert test_file_1.read() == b''
    assert test_file_2.read() == b''
    bit_req._reset_file_positions(file_tuple, None)
    assert test_file_1.read() == b'First message.'
    assert test_file_2.read() == b'Second message.'

    # Test a single file
    file_single = test_file_1
    assert test_file_1.read() == b''
    bit_req._reset_file_positions(None, file_single)
    assert test_file_1.read() == b'First message.'
