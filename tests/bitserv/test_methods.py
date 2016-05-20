import codecs
import pytest
import two1.bitcoin as bitcoin

from two1.bitserv import OnChain
from two1.bitserv.models import OnChainSQLite3
from two1.wallet import Two1Wallet

from two1.bitserv.payment_methods import InsufficientPaymentError
from two1.bitserv.payment_methods import InvalidPaymentParameterError
from two1.bitserv.payment_methods import DuplicatePaymentError
from two1.bitserv.payment_methods import TransactionBroadcastError
from two1.bitserv.payment_methods import PaymentBelowDustLimitError


test_wallet = Two1Wallet.import_from_mnemonic(mnemonic='six words test wallet on fleek')


def _build_void_transaction(price=None, address=None):
    price = price or 1000
    address = address or '19tAqnusJv2XoyxsC1UzuBTdG9dCAgafEX'
    _, hash160 = bitcoin.utils.address_to_key_hash(address)
    h = codecs.encode(b'test hash for a fake payment txn', 'hex_codec').decode()
    outpoint = bitcoin.Hash(h)
    inputs = [bitcoin.TransactionInput(
        outpoint=outpoint, outpoint_index=0, script=bitcoin.Script(), sequence_num=0xffffffff
    )]
    outputs = [bitcoin.TransactionOutput(value=price, script=bitcoin.Script.build_p2pkh(hash160))]
    txn = bitcoin.Transaction(
        version=bitcoin.Transaction.DEFAULT_TRANSACTION_VERSION, inputs=inputs, outputs=outputs, lock_time=0
    )
    return txn


def _mock_broadcast_failure(raw_tx):
    raise Exception('~~~*Something went wrong*~~~')


def _mock_broadcast_success(raw_tx):
    return 'successful txid'


###############################################################################


def test_on_chain_payment_method_headers():
    """Test general header methods in the on-chain payment decorator."""
    test_price = 8888
    test_address = '100MY0000FAKE0000ADDRESS0000'
    test_db = OnChainSQLite3(':memory:', db_dir='')
    requests = OnChain(test_wallet, test_db)

    # Test that it returns a list of payment headers
    payment_headers = requests.payment_headers
    assert isinstance(payment_headers, list)
    assert OnChain.http_payment_data in payment_headers

    # Test that it returns a dict of 402 headers given a price and address
    http_402_headers = requests.get_402_headers(test_price, address=test_address)
    assert isinstance(http_402_headers, dict)
    assert http_402_headers[OnChain.http_402_price] == test_price
    assert http_402_headers[OnChain.http_402_address] == test_address

    # Test that it returns a dict of 402 headers given a price only
    http_402_headers = requests.get_402_headers(test_price)
    assert isinstance(http_402_headers, dict)
    assert http_402_headers[OnChain.http_402_price] == test_price
    assert http_402_headers[OnChain.http_402_address] == test_wallet.get_payout_address()


def test_on_chain_payment_method_redeem_errors():
    """Test redeem_payment method errors in the on-chain payment decorator."""
    test_dust = 100
    test_price = 8888
    test_bad_price = 8887
    test_db = OnChainSQLite3(':memory:', db_dir='')
    requests = OnChain(test_wallet, test_db)

    # Test that a payment less than the dust limit cannot be made
    with pytest.raises(PaymentBelowDustLimitError):
        requests.redeem_payment(test_dust, {'Bitcoin-Transaction': None})

    # Test that a payment can't be made with an invalid transaction format
    with pytest.raises(InvalidPaymentParameterError):
        requests.redeem_payment(test_price, {'Bitcoin-Transaction': None})

    # Test that a payment can't be made to an address that isn't the merchant's
    txn = _build_void_transaction(test_price)
    with pytest.raises(InvalidPaymentParameterError):
        requests.redeem_payment(test_price, {'Bitcoin-Transaction': txn.to_hex()})

    # Test that a payment can't be made for an incorrect amount
    txn = _build_void_transaction(test_bad_price, test_wallet.get_payout_address())
    with pytest.raises(InsufficientPaymentError):
        requests.redeem_payment(test_price, {'Bitcoin-Transaction': txn.to_hex()})

    # Test that a payment already in the database won't be accepted
    txn = _build_void_transaction(test_price, test_wallet.get_payout_address())
    test_db.create(str(txn.hash), test_price)
    with pytest.raises(DuplicatePaymentError):
        requests.redeem_payment(test_price, {'Bitcoin-Transaction': txn.to_hex()})


def test_on_chain_payment_method_redeem_broadcast(monkeypatch):
    """Test broadcast functionality in redeem_payment."""
    test_price = 8888
    test_db = OnChainSQLite3(':memory:', db_dir='')
    requests = OnChain(test_wallet, test_db)
    monkeypatch.setattr(requests.provider, 'broadcast_transaction', _mock_broadcast_failure)

    # Test that errors encountered during broadcast propagate
    with pytest.raises(TransactionBroadcastError):
        txn = _build_void_transaction(test_price, test_wallet.get_payout_address())
        requests.redeem_payment(test_price, {'Bitcoin-Transaction': txn.to_hex()})

    # Test that the failed transaction doesn't persist in the database
    db_txn = test_db.lookup(str(txn.hash))
    assert db_txn is None

    # Test that we can still use the same payment even after a broadcast error
    monkeypatch.setattr(requests.provider, 'broadcast_transaction', _mock_broadcast_success)
    requests.redeem_payment(test_price, {'Bitcoin-Transaction': txn.to_hex()})
    db_txn = test_db.lookup(str(txn.hash))
    assert db_txn['txid'] == str(txn.hash)
    assert db_txn['amount'] == test_price


def test_on_chain_payment_method_redeem_success(monkeypatch):
    """Test success in redeem_payment."""
    test_price = 8888
    test_db = OnChainSQLite3(':memory:', db_dir='')
    requests = OnChain(test_wallet, test_db)
    monkeypatch.setattr(requests.provider, 'broadcast_transaction', _mock_broadcast_success)

    # Test that we can redeem a proper payment
    txn = _build_void_transaction(test_price, test_wallet.get_payout_address())
    requests.redeem_payment(test_price, {'Bitcoin-Transaction': txn.to_hex()})
    db_txn = test_db.lookup(str(txn.hash))
    assert db_txn['txid'] == str(txn.hash)
    assert db_txn['amount'] == test_price

    # Test that we cannot re-use the same payment
    with pytest.raises(DuplicatePaymentError):
        requests.redeem_payment(test_price, {'Bitcoin-Transaction': txn.to_hex()})
