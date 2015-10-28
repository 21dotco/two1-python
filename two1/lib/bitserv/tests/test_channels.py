"""Tests for payment channel functionality."""
import os
import time
import codecs
import pytest
from two1.lib.bitcoin import Script
from two1.lib.bitserv.helpers.blockchain import MockBlockchain
from two1.lib.bitserv.helpers.wallet import Two1WalletWrapper, MockTwo1Wallet
from two1.lib.bitserv.payment_server import PaymentServer, PaymentServerError
from two1.lib.bitserv.models import DatabaseSQLite3

TEST_DEP_AMOUNT = 100000
TEST_PMT_AMOUNT = 5000
TEST_FEE_AMOUNT = 10000
cust_wallet = MockTwo1Wallet()
merch_wallet = MockTwo1Wallet()
server = PaymentServer(merch_wallet, testnet=True)
server._blockchain = MockBlockchain()


def _create_client_txs():
    """Mock client transactions for opening a channel."""
    # Collect public keys
    deposit = TEST_DEP_AMOUNT
    expiration_time = int(time.time() + 86400)
    customer_public_key = cust_wallet.get_payout_public_key()
    merchant_public_key = merch_wallet.get_payout_public_key()

    # Build redeem script
    pubkeys = [customer_public_key.compressed_bytes,
               merchant_public_key.compressed_bytes]
    redeem_script = Script.build_multisig_redeem(2, pubkeys)

    # Build deposit tx
    deposit_tx = cust_wallet.create_deposit_tx(
        redeem_script.hash160())

    # Build refund tx
    refund_tx = cust_wallet.create_refund_tx(
        deposit_tx, redeem_script, customer_public_key, expiration_time,
        TEST_FEE_AMOUNT)

    # Build payment tx
    payment_tx = cust_wallet.create_payment_tx(
        deposit_tx, redeem_script, merchant_public_key,
        customer_public_key, TEST_PMT_AMOUNT, TEST_FEE_AMOUNT)

    return deposit_tx, refund_tx, payment_tx


def test_discovery():
    """Test ability to discover a new payment channel."""
    server._db = DatabaseSQLite3(':memory:')
    merchant_public_key = server.discovery()
    test_public_key = codecs.encode(
        merch_wallet._private_key.public_key.compressed_bytes,
        'hex_codec').decode('utf-8')
    assert merchant_public_key == test_public_key


def test_initialize_handshake():
    """Test ability to initialize a payment channel handshake."""
    server._db = DatabaseSQLite3(':memory:')
    # Create refund transaction using test data utility
    _, refund_tx, _ = _create_client_txs()

    # Initialize the handshake and ensure that it returns sucessfully
    initialized = server.initialize_handshake(refund_tx)
    assert initialized

    # Test for handshake failure when using the same refund twice
    with pytest.raises(PaymentServerError):
        initialized = server.initialize_handshake(refund_tx)


def test_complete_handshake():
    """Test ability to complete a payment channel handshake."""
    server._db = DatabaseSQLite3(':memory:')
    # Create deposit and refund transactions using test data utility
    deposit_tx, refund_tx, _ = _create_client_txs()
    deposit_txid = str(deposit_tx.hash)

    # Test that handshake completion fails when no channel exists
    with pytest.raises(PaymentServerError):
        server.complete_handshake(deposit_txid, deposit_tx)

    # Test that handshake completion succeeds
    server.initialize_handshake(refund_tx)
    completed = server.complete_handshake(deposit_txid, deposit_tx)
    assert completed

    # Test that handshake completion fails with a duplicate deposit
    with pytest.raises(PaymentServerError):
        server.complete_handshake(deposit_txid, deposit_tx)


def test_receive_payment():
    """Test ability to receive a payment within a channel."""
    server._db = DatabaseSQLite3(':memory:')
    deposit_tx, refund_tx, payment_tx = _create_client_txs()
    deposit_txid = str(deposit_tx.hash)

    # Test that payment receipt fails when no channel exists
    with pytest.raises(PaymentServerError):
        server.receive_payment(deposit_txid, payment_tx)

    # Test that payment receipt succeeds
    server.initialize_handshake(refund_tx)
    server.complete_handshake(deposit_txid, deposit_tx)
    paid = server.receive_payment(deposit_txid, payment_tx)
    assert paid

    # Test that payment receipt fails with a duplicate payment
    with pytest.raises(PaymentServerError):
        server.receive_payment(deposit_txid, payment_tx)


def test_redeem_payment():
    """Test ability to redeem a payment made within a channel."""
    server._db = DatabaseSQLite3(':memory:')
    deposit_tx, refund_tx, payment_tx = _create_client_txs()
    deposit_txid = str(deposit_tx.hash)
    payment_txid = str(payment_tx.hash)

    # Test that payment redeem fails when no channel exists
    with pytest.raises(PaymentServerError):
        server.redeem(payment_txid)

    # Test that payment redeem succeeds
    server.initialize_handshake(refund_tx)
    server.complete_handshake(deposit_txid, deposit_tx)
    server.receive_payment(deposit_txid, payment_tx)

    amount = server.redeem(str(payment_tx.hash))
    assert amount == TEST_PMT_AMOUNT

    # Test that payment redeem fails with a duplicate payment
    with pytest.raises(PaymentServerError):
        server.redeem(payment_txid)


def test_status_close_channel():
    """Test ability to get a channel's status and close it."""
    server._db = DatabaseSQLite3(':memory:')
    deposit_tx, refund_tx, payment_tx = _create_client_txs()
    deposit_txid = str(deposit_tx.hash)

    # Test that channel close fails when no channel exists
    with pytest.raises(PaymentServerError):
        server.close(deposit_txid)

    # Test that channel close succeeds
    server.initialize_handshake(refund_tx)
    server.complete_handshake(deposit_txid, deposit_tx)
    server.receive_payment(deposit_txid, payment_tx)
    server.redeem(str(payment_tx.hash))

    closed = server.close(deposit_txid)
    assert closed
