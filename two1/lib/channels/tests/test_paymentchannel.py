import time
import pytest

import two1.lib.channels.statemachine as statemachine
import two1.lib.channels.paymentchannel as paymentchannel
import two1.lib.channels.walletwrapper as walletwrapper
import two1.lib.channels.database as database
import two1.lib.channels.tests.mock as mock


# Monkey-patch mock payment channel server protocol
paymentchannel.SupportedProtocols['mock'] = mock.MockPaymentChannelServer


def test_paymentchannel_typical():
    # Create mocked dependencies
    wallet = walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet())
    db = database.Sqlite3Database(":memory:")
    bc = mock.MockBlockchain()

    # Link the mock blockchain to the mock payment channel server as it is a
    # non-injected dependency.
    mock.MockPaymentChannelServer.blockchain = bc
    # Clear mock payment channel server channels.
    mock.MockPaymentChannelServer.channels = {}

    # Open a payment channel with 100000 deposit, 86400 seconds expiration, and 10000 fee
    pc = paymentchannel.PaymentChannel.open(db, wallet, bc, 'mock://test', 100000, 86400, 10000, False)

    # Check payment channel properties
    assert pc.url == "mock://test/" + pc.deposit_txid
    assert pc.state == statemachine.PaymentChannelState.CONFIRMING_DEPOSIT
    assert pc.ready == False
    assert pc.balance == 100000
    assert pc.deposit == 100000
    assert pc.fee == 10000
    assert pc.creation_time > 0
    assert pc.expiration_time == int(pc.creation_time + 86400)
    assert pc.expired == False
    assert pc.refund_tx
    assert pc.refund_txid
    assert pc.deposit_tx
    assert pc.deposit_txid
    assert pc.payment_tx is None
    assert pc.spend_tx is None
    assert pc.spend_txid is None

    # Check database
    with db:
        assert db.list() == [pc.url]
        assert db.read(pc.url)

    # Check blockchain
    assert bc.check_confirmed(pc.deposit_txid) == False
    assert bc.lookup_tx(pc.deposit_txid) == pc.deposit_tx

    # Try premature payment
    with pytest.raises(paymentchannel.NotReadyError):
        pc.pay(1)

    # Try premature close
    with pytest.raises(paymentchannel.NotReadyError):
        pc.close()

    # Sync payment channel
    pc.sync()
    assert pc.state == statemachine.PaymentChannelState.CONFIRMING_DEPOSIT
    assert pc.ready == False

    # Confirm deposit
    bc.mock_confirm(pc.deposit_txid)

    # Sync payment channel
    pc.sync()
    assert pc.state == statemachine.PaymentChannelState.READY
    assert pc.ready == True

    # Try excess payment
    with pytest.raises(paymentchannel.InsufficientBalanceError):
        pc.pay(pc.balance + 1)

    # Try premature close
    with pytest.raises(paymentchannel.NoPaymentError):
        pc.close()

    # Make regular payments
    assert pc.pay(1500)
    assert pc.balance == 98500
    assert pc.pay(1)
    assert pc.balance == 98499
    assert pc.pay(15)
    assert pc.balance == 98484
    assert pc.pay(20000)
    assert pc.balance == 78484

    # Close payment channel
    pc.close()

    # Check payment channel properties
    assert pc.url == "mock://test/" + pc.deposit_txid
    assert pc.state == statemachine.PaymentChannelState.CONFIRMING_SPEND
    assert pc.ready == False
    assert pc.balance == 78484
    assert pc.deposit == 100000
    assert pc.fee == 10000
    assert pc.creation_time > 0
    assert pc.expiration_time == int(pc.creation_time + 86400)
    assert pc.expired == False
    assert pc.refund_tx
    assert pc.refund_txid
    assert pc.deposit_tx
    assert pc.deposit_txid
    assert pc.payment_tx
    assert pc.spend_tx is None
    assert pc.spend_txid == str(mock.MockPaymentChannelServer.channels[pc.deposit_txid]['payment_tx'].hash)

    # Sync payment channel
    pc.sync()
    assert pc.state == statemachine.PaymentChannelState.CONFIRMING_SPEND

    # Confirm spend
    bc.mock_confirm(pc.spend_txid)

    # Sync payment channel
    pc.sync()
    assert pc.state == statemachine.PaymentChannelState.CLOSED
    assert pc.spend_tx == mock.MockPaymentChannelServer.channels[pc.deposit_txid]['payment_tx'].to_hex()

    # Try payment on closed channel
    with pytest.raises(paymentchannel.ClosedError):
        pc.pay(1)


def test_paymentchannel_typical_zeroconf():
    # Create mocked dependencies
    wallet = walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet())
    db = database.Sqlite3Database(":memory:")
    bc = mock.MockBlockchain()

    # Link the mock blockchain to the mock payment channel server as it is a
    # non-injected dependency.
    mock.MockPaymentChannelServer.blockchain = bc
    # Clear mock payment channel server channels.
    mock.MockPaymentChannelServer.channels = {}

    # Open a payment channel with 100000 deposit, 86400 seconds expiration, and 10000 fee
    pc = paymentchannel.PaymentChannel.open(db, wallet, bc, 'mock://test', 100000, 86400, 10000, True)

    # Check payment channel properties
    assert pc.url == "mock://test/" + pc.deposit_txid
    assert pc.state == statemachine.PaymentChannelState.READY
    assert pc.ready == True
    assert pc.balance == 100000
    assert pc.deposit == 100000
    assert pc.fee == 10000
    assert pc.creation_time > 0
    assert pc.expiration_time == int(pc.creation_time + 86400)
    assert pc.expired == False
    assert pc.refund_tx
    assert pc.refund_txid
    assert pc.deposit_tx
    assert pc.deposit_txid
    assert pc.payment_tx is None
    assert pc.spend_tx is None
    assert pc.spend_txid is None

    # Make a few payments and close the channel
    pc.pay(1)
    pc.pay(1)
    pc.pay(1)
    pc.close()

    # Check payment channel properties
    assert pc.url == "mock://test/" + pc.deposit_txid
    assert pc.state == statemachine.PaymentChannelState.CONFIRMING_SPEND
    assert pc.ready == False
    assert pc.balance == 98998
    assert pc.deposit == 100000
    assert pc.fee == 10000
    assert pc.creation_time > 0
    assert pc.expiration_time == int(pc.creation_time + 86400)
    assert pc.expired == False
    assert pc.refund_tx
    assert pc.refund_txid
    assert pc.deposit_tx
    assert pc.deposit_txid
    assert pc.payment_tx
    assert pc.spend_tx is None
    assert pc.spend_txid


def test_paymentchannel_expiration():
    # Create mocked dependencies
    wallet = walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet())
    db = database.Sqlite3Database(":memory:")
    bc = mock.MockBlockchain()

    # Link the mock blockchain to the mock payment channel server as it is a
    # non-injected dependency.
    mock.MockPaymentChannelServer.blockchain = bc
    # Clear mock payment channel server channels.
    mock.MockPaymentChannelServer.channels = {}

    # Open a payment channel with 100000 deposit, 86400 seconds expiration, and 10000 fee
    pc = paymentchannel.PaymentChannel.open(db, wallet, bc, 'mock://test', 100000, 86400, 10000, False)

    # Confirm the deposit tx
    bc.mock_confirm(pc.deposit_txid)
    pc.sync()

    # Check payment channel properties
    assert pc.url == "mock://test/" + pc.deposit_txid
    assert pc.state == statemachine.PaymentChannelState.READY
    assert pc.ready == True
    assert pc.balance == 100000
    assert pc.deposit == 100000
    assert pc.fee == 10000
    assert pc.creation_time > 0
    assert pc.expiration_time == int(pc.creation_time + 86400)
    assert pc.expired == False
    assert pc.refund_tx
    assert pc.refund_txid
    assert pc.deposit_tx
    assert pc.deposit_txid
    assert pc.payment_tx is None
    assert pc.spend_tx is None
    assert pc.spend_txid is None

    # Make a few payments
    pc.pay(1)
    pc.pay(1)
    pc.pay(1)

    # Check payment channel properties
    assert pc.expired == False

    # Monkey-patch time.time() for expiration
    orig_time_time = time.time
    time.time = lambda: pc.expiration_time + 1

    # Check payment channel properties
    assert pc.url == "mock://test/" + pc.deposit_txid
    assert pc.state == statemachine.PaymentChannelState.READY
    assert pc.ready == True
    assert pc.balance == 98998
    assert pc.deposit == 100000
    assert pc.fee == 10000
    assert pc.creation_time > 0
    assert pc.expiration_time == int(pc.creation_time + 86400)
    assert pc.expired == True
    assert pc.refund_tx
    assert pc.refund_txid
    assert pc.deposit_tx
    assert pc.deposit_txid
    assert pc.payment_tx
    assert pc.spend_tx is None
    assert pc.spend_txid is None

    # Sync to trigger a refund
    pc.sync()

    # Check payment channel properties
    assert pc.url == "mock://test/" + pc.deposit_txid
    assert pc.state == statemachine.PaymentChannelState.CONFIRMING_SPEND
    assert pc.ready == False
    assert pc.balance == 98998
    assert pc.deposit == 100000
    assert pc.fee == 10000
    assert pc.creation_time > 0
    assert pc.expiration_time == int(pc.creation_time + 86400)
    assert pc.expired == True
    assert pc.refund_tx
    assert pc.refund_txid
    assert pc.deposit_tx
    assert pc.deposit_txid
    assert pc.payment_tx
    assert pc.spend_tx is None
    assert pc.spend_txid == pc.refund_txid

    # Confirm refund tx
    bc.mock_confirm(pc.refund_txid)

    # Sync
    pc.sync()

    # Check payment channel properties
    assert pc.url == "mock://test/" + pc.deposit_txid
    assert pc.state == statemachine.PaymentChannelState.CLOSED
    assert pc.ready == False
    assert pc.balance == 100000
    assert pc.deposit == 100000
    assert pc.fee == 10000
    assert pc.creation_time > 0
    assert pc.expiration_time == int(pc.creation_time + 86400)
    assert pc.expired == True
    assert pc.refund_tx
    assert pc.refund_txid
    assert pc.deposit_tx
    assert pc.deposit_txid
    assert pc.payment_tx
    assert pc.spend_tx == pc.refund_tx
    assert pc.spend_txid == pc.refund_txid

    # Restore time.time()
    time.time = orig_time_time


# Server-side close open(), pay(), pay(), <close>, pay(), sync()

def test_paymentchannel_serverside_close():
    # Create mocked dependencies
    wallet = walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet())
    db = database.Sqlite3Database(":memory:")
    bc = mock.MockBlockchain()

    # Link the mock blockchain to the mock payment channel server as it is a
    # non-injected dependency.
    mock.MockPaymentChannelServer.blockchain = bc
    # Clear mock payment channel server channels.
    mock.MockPaymentChannelServer.channels = {}

    # Open a payment channel with 100000 deposit, 86400 seconds expiration, and 10000 fee
    pc = paymentchannel.PaymentChannel.open(db, wallet, bc, 'mock://test', 100000, 86400, 10000, False)

    # Confirm the deposit tx
    bc.mock_confirm(pc.deposit_txid)
    pc.sync()

    # Check payment channel properties
    assert pc.url == "mock://test/" + pc.deposit_txid
    assert pc.state == statemachine.PaymentChannelState.READY
    assert pc.ready == True
    assert pc.balance == 100000
    assert pc.deposit == 100000
    assert pc.fee == 10000
    assert pc.creation_time > 0
    assert pc.expiration_time == int(pc.creation_time + 86400)
    assert pc.expired == False
    assert pc.refund_tx
    assert pc.refund_txid
    assert pc.deposit_tx
    assert pc.deposit_txid
    assert pc.payment_tx is None
    assert pc.spend_tx is None
    assert pc.spend_txid is None

    # Make a few payments
    pc.pay(1)
    pc.pay(1)
    pc.pay(1)

    # Check payment channel properties
    assert pc.url == "mock://test/" + pc.deposit_txid
    assert pc.state == statemachine.PaymentChannelState.READY
    assert pc.ready == True
    assert pc.balance == 98998
    assert pc.deposit == 100000
    assert pc.fee == 10000
    assert pc.creation_time > 0
    assert pc.expiration_time == int(pc.creation_time + 86400)
    assert pc.expired == False
    assert pc.refund_tx
    assert pc.refund_txid
    assert pc.deposit_tx
    assert pc.deposit_txid
    assert pc.payment_tx
    assert pc.spend_tx is None
    assert pc.spend_txid is None

    # Close the channel server-side by broadcasting the last payment tx
    bc.broadcast_tx(mock.MockPaymentChannelServer.channels[pc.deposit_txid]['payment_tx'].to_hex())

    # Sync
    pc.sync()

    # Check payment channel properties
    assert pc.url == "mock://test/" + pc.deposit_txid
    assert pc.state == statemachine.PaymentChannelState.CONFIRMING_SPEND
    assert pc.ready == False
    assert pc.balance == 98998
    assert pc.deposit == 100000
    assert pc.fee == 10000
    assert pc.creation_time > 0
    assert pc.expiration_time == int(pc.creation_time + 86400)
    assert pc.expired == False
    assert pc.refund_tx
    assert pc.refund_txid
    assert pc.deposit_tx
    assert pc.deposit_txid
    assert pc.payment_tx
    assert pc.spend_tx is None
    assert pc.spend_txid == str(mock.MockPaymentChannelServer.channels[pc.deposit_txid]['payment_tx'].hash)

    # Confirm payment tx
    bc.mock_confirm(pc.spend_txid)

    # Sync
    pc.sync()

    # Check payment channel properties
    assert pc.url == "mock://test/" + pc.deposit_txid
    assert pc.state == statemachine.PaymentChannelState.CLOSED
    assert pc.ready == False
    assert pc.balance == 98998
    assert pc.deposit == 100000
    assert pc.fee == 10000
    assert pc.creation_time > 0
    assert pc.expiration_time == int(pc.creation_time + 86400)
    assert pc.expired == False
    assert pc.refund_tx
    assert pc.refund_txid
    assert pc.deposit_tx
    assert pc.deposit_txid
    assert pc.payment_tx
    assert pc.spend_tx == mock.MockPaymentChannelServer.channels[pc.deposit_txid]['payment_tx'].to_hex()
    assert pc.spend_txid == str(mock.MockPaymentChannelServer.channels[pc.deposit_txid]['payment_tx'].hash)
