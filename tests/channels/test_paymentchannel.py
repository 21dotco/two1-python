import time
import pytest

import two1.channels.statemachine as statemachine
import two1.channels.paymentchannel as paymentchannel
import two1.channels.walletwrapper as walletwrapper
import two1.channels.database as database
import tests.channels.mock as mock


# Monkey-patch mock payment channel server protocol
paymentchannel.SupportedProtocols['mock'] = mock.MockPaymentChannelServer


def assert_paymentchannel_state(expected, actual):
    for attr in expected:
        if callable(expected[attr]):
            assert expected[attr](actual)
        else:
            assert expected[attr] == getattr(actual, attr)


def test_paymentchannel_typical():
    # Create mocked dependencies
    bc = mock.MockBlockchain()
    wallet = walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet(), bc)
    db = database.Sqlite3Database(":memory:")

    # Link the mock blockchain to the mock payment channel server as it is a
    # non-injected dependency.
    mock.MockPaymentChannelServer.blockchain = bc
    # Clear mock payment channel server channels.
    mock.MockPaymentChannelServer.channels = {}

    # Open a payment channel with 100000 deposit, 86400 seconds expiration, and 30000 fee
    pc = paymentchannel.PaymentChannel.open(db, wallet, bc, 'mock://test', 100000, 86400, 30000, False)

    # Assert payment channel properties
    expected_state = {}
    expected_state['url'] = "mock://test/" + pc.deposit_txid
    expected_state['state'] = statemachine.PaymentChannelState.CONFIRMING_DEPOSIT
    expected_state['ready'] = False
    expected_state['balance'] = 100000
    expected_state['deposit'] = 100000
    expected_state['fee'] = 30000
    expected_state['creation_time'] = lambda pc: pc.creation_time > 0
    expected_state['expiration_time'] = int(pc.creation_time + 86400)
    expected_state['expired'] = False
    expected_state['refund_tx'] = lambda pc: pc.refund_tx
    expected_state['refund_txid'] = lambda pc: pc.refund_txid
    expected_state['deposit_tx'] = lambda pc: pc.deposit_tx
    expected_state['deposit_txid'] = lambda pc: pc.deposit_txid
    expected_state['payment_tx'] = None
    expected_state['spend_tx'] = None
    expected_state['spend_txid'] = None
    assert_paymentchannel_state(expected_state, pc)

    # Check database
    with db:
        assert db.list() == [pc.url]
        assert db.read(pc.url)

    # Check blockchain
    assert bc.check_confirmed(pc.deposit_txid) is False
    assert bc.lookup_tx(pc.deposit_txid) == pc.deposit_tx

    # Try premature payment
    with pytest.raises(paymentchannel.NotReadyError):
        pc.pay(1)

    # Try premature close
    with pytest.raises(paymentchannel.NotReadyError):
        pc.close()

    # Sync payment channel
    pc.sync()
    expected_state['state'] = statemachine.PaymentChannelState.CONFIRMING_DEPOSIT
    expected_state['ready'] = False
    assert_paymentchannel_state(expected_state, pc)

    # Confirm deposit
    bc.mock_confirm(pc.deposit_txid)

    # Sync payment channel
    pc.sync()
    expected_state['state'] = statemachine.PaymentChannelState.READY
    expected_state['ready'] = True
    assert_paymentchannel_state(expected_state, pc)

    # Try excess payment
    with pytest.raises(paymentchannel.InsufficientBalanceError):
        pc.pay(pc.balance + 1)

    # Try premature close
    with pytest.raises(paymentchannel.NoPaymentError):
        pc.close()

    # Make regular payments
    assert pc.pay(1500)
    expected_state['payment_tx'] = lambda pc: pc.payment_tx
    expected_state['balance'] = 97000
    assert_paymentchannel_state(expected_state, pc)
    assert pc.pay(1)
    expected_state['payment_tx'] = lambda pc: pc.payment_tx
    expected_state['balance'] = 96999
    assert_paymentchannel_state(expected_state, pc)
    assert pc.pay(15)
    expected_state['payment_tx'] = lambda pc: pc.payment_tx
    expected_state['balance'] = 96984
    assert_paymentchannel_state(expected_state, pc)
    assert pc.pay(20000)
    expected_state['payment_tx'] = lambda pc: pc.payment_tx
    expected_state['balance'] = 76984
    assert_paymentchannel_state(expected_state, pc)

    # Close payment channel
    pc.close()

    # Check payment channel properties
    expected_state['state'] = statemachine.PaymentChannelState.CONFIRMING_SPEND
    expected_state['ready'] = False
    expected_state['spend_txid'] = str(mock.MockPaymentChannelServer.channels[pc.deposit_txid]['payment_tx'].hash)
    assert_paymentchannel_state(expected_state, pc)

    # Sync payment channel
    pc.sync()
    assert_paymentchannel_state(expected_state, pc)

    # Confirm spend
    bc.mock_confirm(pc.spend_txid)

    # Sync payment channel
    pc.sync()
    expected_state['state'] = statemachine.PaymentChannelState.CLOSED
    expected_state['spend_tx'] = mock.MockPaymentChannelServer.channels[pc.deposit_txid]['payment_tx'].to_hex()
    assert_paymentchannel_state(expected_state, pc)

    # Try payment on closed channel
    with pytest.raises(paymentchannel.ClosedError):
        pc.pay(1)


def test_paymentchannel_typical_zeroconf():
    # Create mocked dependencies
    bc = mock.MockBlockchain()
    wallet = walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet(), bc)
    db = database.Sqlite3Database(":memory:")

    # Link the mock blockchain to the mock payment channel server as it is a
    # non-injected dependency.
    mock.MockPaymentChannelServer.blockchain = bc
    # Clear mock payment channel server channels.
    mock.MockPaymentChannelServer.channels = {}

    # Open a payment channel with 100000 deposit, 86400 seconds expiration, and 30000 fee
    pc = paymentchannel.PaymentChannel.open(db, wallet, bc, 'mock://test', 100000, 86400, 30000, True)

    # Assert payment channel properties
    expected_state = {}
    expected_state['url'] = "mock://test/" + pc.deposit_txid
    expected_state['state'] = statemachine.PaymentChannelState.READY
    expected_state['ready'] = True
    expected_state['balance'] = 100000
    expected_state['deposit'] = 100000
    expected_state['fee'] = 30000
    expected_state['creation_time'] = lambda pc: pc.creation_time > 0
    expected_state['expiration_time'] = int(pc.creation_time + 86400)
    expected_state['expired'] = False
    expected_state['refund_tx'] = lambda pc: pc.refund_tx
    expected_state['refund_txid'] = lambda pc: pc.refund_txid
    expected_state['deposit_tx'] = lambda pc: pc.deposit_tx
    expected_state['deposit_txid'] = lambda pc: pc.deposit_txid
    expected_state['payment_tx'] = None
    expected_state['spend_tx'] = None
    expected_state['spend_txid'] = None
    assert_paymentchannel_state(expected_state, pc)

    # Make a few payments and close the channel
    pc.pay(1)
    pc.pay(1)
    pc.pay(1)
    pc.close()

    # Check payment channel properties
    expected_state['state'] = statemachine.PaymentChannelState.CONFIRMING_SPEND
    expected_state['ready'] = False
    expected_state['payment_tx'] = lambda pc: pc.payment_tx
    expected_state['balance'] = 96998
    expected_state['spend_txid'] = lambda pc: pc.spend_txid
    assert_paymentchannel_state(expected_state, pc)


def test_paymentchannel_expiration():
    # Create mocked dependencies
    bc = mock.MockBlockchain()
    wallet = walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet(), bc)
    db = database.Sqlite3Database(":memory:")

    # Link the mock blockchain to the mock payment channel server as it is a
    # non-injected dependency.
    mock.MockPaymentChannelServer.blockchain = bc
    # Clear mock payment channel server channels.
    mock.MockPaymentChannelServer.channels = {}

    # Open a payment channel with 100000 deposit, 86400 seconds expiration, and 30000 fee
    pc = paymentchannel.PaymentChannel.open(db, wallet, bc, 'mock://test', 100000, 86400, 30000, False)

    # Confirm the deposit tx
    bc.mock_confirm(pc.deposit_txid)
    pc.sync()

    # Assert payment channel properties
    expected_state = {}
    expected_state['url'] = "mock://test/" + pc.deposit_txid
    expected_state['state'] = statemachine.PaymentChannelState.READY
    expected_state['ready'] = True
    expected_state['balance'] = 100000
    expected_state['deposit'] = 100000
    expected_state['fee'] = 30000
    expected_state['creation_time'] = lambda pc: pc.creation_time > 0
    expected_state['expiration_time'] = int(pc.creation_time + 86400)
    expected_state['expired'] = False
    expected_state['refund_tx'] = lambda pc: pc.refund_tx
    expected_state['refund_txid'] = lambda pc: pc.refund_txid
    expected_state['deposit_tx'] = lambda pc: pc.deposit_tx
    expected_state['deposit_txid'] = lambda pc: pc.deposit_txid
    expected_state['payment_tx'] = None
    expected_state['spend_tx'] = None
    expected_state['spend_txid'] = None
    assert_paymentchannel_state(expected_state, pc)

    # Make a few payments
    pc.pay(1)
    pc.pay(1)
    pc.pay(1)

    # Check payment channel properties
    expected_state['balance'] = 96998
    expected_state['expired'] = False
    expected_state['payment_tx'] = lambda pc: pc.payment_tx
    assert_paymentchannel_state(expected_state, pc)

    # Monkey-patch time.time() for expiration
    orig_time_time = time.time
    time.time = lambda: pc.expiration_time + paymentchannel.PaymentChannel.REFUND_BROADCAST_TIME_OFFSET + 1

    # Check payment channel properties
    expected_state['expired'] = True
    assert_paymentchannel_state(expected_state, pc)

    # Sync to trigger a refund
    pc.sync()

    # Check payment channel properties
    expected_state['state'] = statemachine.PaymentChannelState.CONFIRMING_SPEND
    expected_state['ready'] = False
    expected_state['expired'] = True
    expected_state['spend_txid'] = lambda pc: pc.refund_txid
    assert_paymentchannel_state(expected_state, pc)

    # Confirm refund tx
    bc.mock_confirm(pc.refund_txid)

    # Sync
    pc.sync()

    # Check payment channel properties
    expected_state['state'] = statemachine.PaymentChannelState.CLOSED
    expected_state['spend_tx'] = lambda pc: pc.refund_tx

    # Restore time.time()
    time.time = orig_time_time


# Server-side close open(), pay(), pay(), <close>, pay(), sync()

def test_paymentchannel_serverside_close():
    # Create mocked dependencies
    bc = mock.MockBlockchain()
    wallet = walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet(), bc)
    db = database.Sqlite3Database(":memory:")

    # Link the mock blockchain to the mock payment channel server as it is a
    # non-injected dependency.
    mock.MockPaymentChannelServer.blockchain = bc
    # Clear mock payment channel server channels.
    mock.MockPaymentChannelServer.channels = {}

    # Open a payment channel with 100000 deposit, 86400 seconds expiration, and 30000 fee
    pc = paymentchannel.PaymentChannel.open(db, wallet, bc, 'mock://test', 100000, 86400, 30000, False)

    # Confirm the deposit tx
    bc.mock_confirm(pc.deposit_txid)
    pc.sync()

    # Assert payment channel properties
    expected_state = {}
    expected_state['url'] = "mock://test/" + pc.deposit_txid
    expected_state['state'] = statemachine.PaymentChannelState.READY
    expected_state['ready'] = True
    expected_state['balance'] = 100000
    expected_state['deposit'] = 100000
    expected_state['fee'] = 30000
    expected_state['creation_time'] = lambda pc: pc.creation_time > 0
    expected_state['expiration_time'] = int(pc.creation_time + 86400)
    expected_state['expired'] = False
    expected_state['refund_tx'] = lambda pc: pc.refund_tx
    expected_state['refund_txid'] = lambda pc: pc.refund_txid
    expected_state['deposit_tx'] = lambda pc: pc.deposit_tx
    expected_state['deposit_txid'] = lambda pc: pc.deposit_txid
    expected_state['payment_tx'] = None
    expected_state['spend_tx'] = None
    expected_state['spend_txid'] = None
    assert_paymentchannel_state(expected_state, pc)

    # Make a few payments
    pc.pay(1)
    pc.pay(1)
    pc.pay(1)

    # Check payment channel properties
    expected_state['balance'] = 96998
    expected_state['expired'] = False
    expected_state['payment_tx'] = lambda pc: pc.payment_tx
    assert_paymentchannel_state(expected_state, pc)

    # Close the channel server-side by broadcasting the last payment tx
    bc.broadcast_tx(mock.MockPaymentChannelServer.channels[pc.deposit_txid]['payment_tx'].to_hex())

    # Sync
    pc.sync()

    # Check payment channel properties
    expected_state['state'] = statemachine.PaymentChannelState.CONFIRMING_SPEND
    expected_state['ready'] = False
    expected_state['spend_txid'] = lambda pc: pc.spend_txid
    assert_paymentchannel_state(expected_state, pc)

    # Confirm payment tx
    bc.mock_confirm(pc.spend_txid)

    # Sync
    pc.sync()

    # Check payment channel properties
    expected_state['state'] = statemachine.PaymentChannelState.CLOSED
    expected_state['spend_tx'] = lambda pc: pc.spend_tx
    assert_paymentchannel_state(expected_state, pc)
