import json
import pytest
from two1.commands.config import Config
from two1.lib.bitcurl.bitrequests import BitTransferRequests
from two1.lib.bitcurl.bitrequests import OnChainRequests
from two1.lib.bitcurl.bitrequests import BitRequestsError
from two1.lib.bitcurl.bitrequests import BitRequests


class MockRequest:
    pass


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
