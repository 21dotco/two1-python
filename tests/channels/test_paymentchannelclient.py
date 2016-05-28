import time
import pytest

import two1.bitcoin as bitcoin
import two1.channels.paymentchannelclient as paymentchannelclient
import two1.channels.statemachine as statemachine
import two1.channels.paymentchannel as paymentchannel
import two1.channels.database as database
import tests.channels.mock as mock


# Monkey-patch mock payment channel server protocol
paymentchannel.SupportedProtocols['mock'] = mock.MockPaymentChannelServer


def assert_paymentchannel_status(expected, actual):
    for attr in expected:
        if callable(expected[attr]):
            assert expected[attr](actual)
        else:
            assert expected[attr] == getattr(actual, attr)


def test_paymentchannelclient():
    # Create mocked dependencies
    wallet = mock.MockTwo1Wallet()
    db = database.Sqlite3Database(":memory:")
    bc = mock.MockBlockchain()

    # Link the mock blockchain to the mock payment channel server as it is a
    # non-injected dependency.
    mock.MockPaymentChannelServer.blockchain = bc
    # Clear mock payment channel server channels.
    mock.MockPaymentChannelServer.channels = {}

    # Create a payment channel client
    pc = paymentchannelclient.PaymentChannelClient(wallet, _database=db, _blockchain=bc)

    # Check channel list
    assert pc.list() == []

    # Open a payment channel with 100000 deposit, 86400 seconds expiration, and 10000 fee
    url1 = pc.open('mock://test', 100000, 86400, 10000, False)

    # Open a payment channel with 300000 deposit, 50000 seconds expiration, and 20000 fee
    url2 = pc.open('mock://test', 300000, 50000, 20000, True)

    # Check channel list
    assert len(pc.list()) == 2

    # Check url1 properties
    status = pc.status(url1)
    url1_expected_status = {}
    url1_expected_status['url'] = lambda status: "mock://test/" + status.deposit_txid
    url1_expected_status['state'] = statemachine.PaymentChannelState.CONFIRMING_DEPOSIT
    url1_expected_status['ready'] = False
    url1_expected_status['balance'] = 100000
    url1_expected_status['deposit'] = 100000
    url1_expected_status['fee'] = 10000
    url1_expected_status['creation_time'] = lambda status: status.creation_time > 0
    url1_expected_status['expiration_time'] = int(status.creation_time + 86400)
    url1_expected_status['expired'] = False
    url1_expected_status['deposit_txid'] = lambda status: status.deposit_txid
    url1_expected_status['spend_txid'] = None
    assert_paymentchannel_status(url1_expected_status, status)

    # Check url2 properties
    status = pc.status(url2)
    url2_expected_status = {}
    url2_expected_status['url'] = lambda status: "mock://test/" + status.deposit_txid
    url2_expected_status['state'] = statemachine.PaymentChannelState.READY
    url2_expected_status['ready'] = True
    url2_expected_status['balance'] = 300000
    url2_expected_status['deposit'] = 300000
    url2_expected_status['fee'] = 20000
    url2_expected_status['creation_time'] = lambda status: status.creation_time > 0
    url2_expected_status['expiration_time'] = int(status.creation_time + 50000)
    url2_expected_status['expired'] = False
    url2_expected_status['deposit_txid'] = lambda status: status.deposit_txid
    url2_expected_status['spend_txid'] = None
    assert_paymentchannel_status(url2_expected_status, status)

    # Try premature close on url1
    with pytest.raises(paymentchannel.NotReadyError):
        pc.close(url1)

    # Try premature pay on url1
    with pytest.raises(paymentchannel.NotReadyError):
        pc.pay(url1, 1)

    # Confirm url1 deposit
    bc.mock_confirm(pc.status(url1).deposit_txid)

    # Sync channels
    pc.sync()

    # Check url1 readiness
    status = pc.status(url1)
    url1_expected_status['state'] = statemachine.PaymentChannelState.READY
    url1_expected_status['ready'] = True
    assert_paymentchannel_status(url1_expected_status, status)

    # Try to pay to an invalid channel
    with pytest.raises(paymentchannelclient.NotFoundError):
        pc.pay("foo", 1)

    # Try to pay excess amount
    with pytest.raises(paymentchannel.InsufficientBalanceError):
        pc.pay(url1, 500000)

    # Try to close without payment
    with pytest.raises(paymentchannel.NoPaymentError):
        pc.close(url1)

    # Pay to both channels
    pc.pay(url1, 1500)
    pc.pay(url2, 3500)
    pc.pay(url1, 123)
    pc.pay(url2, 1)
    pc.pay(url1, 400)
    pc.pay(url2, 10000)
    pc.pay(url1, 20)
    pc.pay(url2, 3123)

    # Check url1 properties
    status = pc.status(url1)
    url1_expected_status['balance'] = 96457
    assert_paymentchannel_status(url1_expected_status, status)

    # Check url2 properties
    status = pc.status(url2)
    url2_expected_status['balance'] = 283376
    assert_paymentchannel_status(url2_expected_status, status)

    # Close url1
    pc.close(url1)

    # Check url1 properties
    status = pc.status(url1)
    url1_expected_status['state'] = statemachine.PaymentChannelState.CONFIRMING_SPEND
    url1_expected_status['ready'] = False
    url1_expected_status['spend_txid'] = str(
        mock.MockPaymentChannelServer.channels[status.deposit_txid]['payment_tx'].hash)
    assert_paymentchannel_status(url1_expected_status, status)

    # Confirm close
    bc.mock_confirm(status.spend_txid)

    # Sync
    pc.sync()

    # Check url1 properties
    status = pc.status(url1)
    url1_expected_status['state'] = statemachine.PaymentChannelState.CLOSED
    assert_paymentchannel_status(url1_expected_status, status)

    # Check url2 properties
    status = pc.status(url2)
    assert_paymentchannel_status(url2_expected_status, status)

    # Close url2 server-side
    bc.broadcast_tx(mock.MockPaymentChannelServer.channels[status.deposit_txid]['payment_tx'].to_hex())

    # Sync
    pc.sync()

    # Check url1 properties
    status = pc.status(url1)
    assert_paymentchannel_status(url1_expected_status, status)

    # Try pay after close on url1
    with pytest.raises(paymentchannel.ClosedError):
        pc.pay(url1, 1)

    # Check url2 properties
    status = pc.status(url2)
    url2_expected_status['state'] = statemachine.PaymentChannelState.CONFIRMING_SPEND
    url2_expected_status['ready'] = False
    url2_expected_status['spend_txid'] = str(
        mock.MockPaymentChannelServer.channels[status.deposit_txid]['payment_tx'].hash)
    assert_paymentchannel_status(url2_expected_status, status)

    # Confirm close
    bc.mock_confirm(status.spend_txid)

    # Sync
    pc.sync()

    # Check url1 properties
    status = pc.status(url1)
    assert_paymentchannel_status(url1_expected_status, status)

    # Check url2 properties
    status = pc.status(url2)
    url2_expected_status['state'] = statemachine.PaymentChannelState.CLOSED
    assert_paymentchannel_status(url2_expected_status, status)

    # Open a payment channel with 400000 deposit, 50000 seconds expiration, and 20000 fee
    url3 = pc.open('mock://test', 400000, 50000, 20000, True)

    # Check url3 properties
    status = pc.status(url3)
    url3_expected_status = {}
    url3_expected_status['url'] = 'mock://test/' + status.deposit_txid
    url3_expected_status['state'] = statemachine.PaymentChannelState.READY
    url3_expected_status['ready'] = True
    url3_expected_status['balance'] = 400000
    url3_expected_status['deposit'] = 400000
    url3_expected_status['fee'] = 20000
    url3_expected_status['creation_time'] = lambda status: status.creation_time > 0
    url3_expected_status['expiration_time'] = int(status.creation_time + 50000)
    url3_expected_status['expired'] = False
    url3_expected_status['deposit_txid'] = lambda status: status.deposit_txid
    url3_expected_status['spend_txid'] = None
    assert_paymentchannel_status(url3_expected_status, status)

    # Monkey-patch time.time() for expiration
    orig_time_time = time.time
    time.time = lambda: status.expiration_time + paymentchannel.PaymentChannel.REFUND_BROADCAST_TIME_OFFSET + 1

    # Sync
    pc.sync()

    # Check url3 properties
    status = pc.status(url3, include_txs=True)
    url3_expected_status['state'] = statemachine.PaymentChannelState.CONFIRMING_SPEND
    url3_expected_status['ready'] = False
    url3_expected_status['expired'] = True
    url3_expected_status['spend_txid'] = str(bitcoin.Transaction.from_hex(status.transactions.refund_tx).hash)
    assert_paymentchannel_status(url3_expected_status, status)

    # Confirm refund
    bc.mock_confirm(status.spend_txid)

    # Sync
    pc.sync()

    # Check url3 properties
    status = pc.status(url3, include_txs=True)
    url3_expected_status['state'] = statemachine.PaymentChannelState.CLOSED
    assert_paymentchannel_status(url3_expected_status, status)

    # Restore time.time()
    time.time = orig_time_time

    # Ensure all channels are closed
    for url in pc.list():
        assert pc.status(url).state == statemachine.PaymentChannelState.CLOSED
