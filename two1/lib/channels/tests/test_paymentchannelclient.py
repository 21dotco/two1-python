import time
import pytest

import two1.lib.bitcoin as bitcoin
import two1.lib.channels.paymentchannelclient as paymentchannelclient
import two1.lib.channels.statemachine as statemachine
import two1.lib.channels.paymentchannel as paymentchannel
import two1.lib.channels.database as database
import two1.lib.channels.tests.mock as mock


# Monkey-patch mock payment channel server protocol
paymentchannel.SupportedProtocols['mock'] = mock.MockPaymentChannelServer


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
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.CONFIRMING_DEPOSIT
    assert status.ready == False
    assert status.balance == 100000
    assert status.deposit == 100000
    assert status.fee == 10000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 86400)
    assert status.expired == False
    assert status.deposit_txid
    assert status.spend_txid is None

    # Check url2 properties
    status = pc.status(url2)
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.READY
    assert status.ready == True
    assert status.balance == 300000
    assert status.deposit == 300000
    assert status.fee == 20000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 50000)
    assert status.expired == False
    assert status.deposit_txid
    assert status.spend_txid is None

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
    assert status.state == statemachine.PaymentChannelState.READY
    assert status.ready == True

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
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.READY
    assert status.ready == True
    assert status.balance == 97957
    assert status.deposit == 100000
    assert status.fee == 10000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 86400)
    assert status.expired == False
    assert status.deposit_txid
    assert status.spend_txid is None

    # Check url2 properties
    status = pc.status(url2)
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.READY
    assert status.ready == True
    assert status.balance == 283376
    assert status.deposit == 300000
    assert status.fee == 20000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 50000)
    assert status.expired == False
    assert status.deposit_txid
    assert status.spend_txid is None

    # Close url1
    pc.close(url1)

    # Check url1 properties
    status = pc.status(url1)
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.CONFIRMING_SPEND
    assert status.ready == False
    assert status.balance == 97957
    assert status.deposit == 100000
    assert status.fee == 10000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 86400)
    assert status.expired == False
    assert status.deposit_txid
    assert status.spend_txid == str(mock.MockPaymentChannelServer.channels[status.deposit_txid]['payment_tx'].hash)

    # Confirm close
    bc.mock_confirm(status.spend_txid)

    # Sync
    pc.sync()

    # Check url1 properties
    status = pc.status(url1)
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.CLOSED
    assert status.ready == False
    assert status.balance == 97957
    assert status.deposit == 100000
    assert status.fee == 10000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 86400)
    assert status.expired == False
    assert status.deposit_txid
    assert status.spend_txid == str(mock.MockPaymentChannelServer.channels[status.deposit_txid]['payment_tx'].hash)

    # Check url2 properties
    status = pc.status(url2)
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.READY
    assert status.ready == True
    assert status.balance == 283376
    assert status.deposit == 300000
    assert status.fee == 20000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 50000)
    assert status.expired == False
    assert status.deposit_txid
    assert status.spend_txid is None

    # Close url2 server-side
    bc.broadcast_tx(mock.MockPaymentChannelServer.channels[status.deposit_txid]['payment_tx'].to_hex())

    # Sync
    pc.sync()

    # Check url1 properties
    status = pc.status(url1)
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.CLOSED
    assert status.ready == False
    assert status.balance == 97957
    assert status.deposit == 100000
    assert status.fee == 10000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 86400)
    assert status.expired == False
    assert status.deposit_txid
    assert status.spend_txid == str(mock.MockPaymentChannelServer.channels[status.deposit_txid]['payment_tx'].hash)

    # Try pay after close on url1
    with pytest.raises(paymentchannel.ClosedError):
        pc.pay(url1, 1)

    # Check url2 properties
    status = pc.status(url2)
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.CONFIRMING_SPEND
    assert status.ready == False
    assert status.balance == 283376
    assert status.deposit == 300000
    assert status.fee == 20000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 50000)
    assert status.expired == False
    assert status.deposit_txid
    assert status.spend_txid == str(mock.MockPaymentChannelServer.channels[status.deposit_txid]['payment_tx'].hash)

    # Confirm close
    bc.mock_confirm(status.spend_txid)

    # Sync
    pc.sync()

    # Check url1 properties
    status = pc.status(url1)
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.CLOSED
    assert status.ready == False
    assert status.balance == 97957
    assert status.deposit == 100000
    assert status.fee == 10000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 86400)
    assert status.expired == False
    assert status.deposit_txid
    assert status.spend_txid == str(mock.MockPaymentChannelServer.channels[status.deposit_txid]['payment_tx'].hash)

    # Check url2 properties
    status = pc.status(url2)
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.CLOSED
    assert status.ready == False
    assert status.balance == 283376
    assert status.deposit == 300000
    assert status.fee == 20000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 50000)
    assert status.expired == False
    assert status.deposit_txid
    assert status.spend_txid == str(mock.MockPaymentChannelServer.channels[status.deposit_txid]['payment_tx'].hash)

    # Open a payment channel with 400000 deposit, 50000 seconds expiration, and 20000 fee
    url3 = pc.open('mock://test', 400000, 50000, 20000, True)

    # Check url3 properties
    status = pc.status(url3)
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.READY
    assert status.ready == True
    assert status.balance == 400000
    assert status.deposit == 400000
    assert status.fee == 20000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 50000)
    assert status.expired == False
    assert status.deposit_txid
    assert status.spend_txid is None

    # Monkey-patch time.time() for expiration
    orig_time_time = time.time
    time.time = lambda: status.expiration_time + paymentchannel.PaymentChannel.REFUND_BROADCAST_TIME_OFFSET + 1

    # Sync
    pc.sync()

    # Check url3 properties
    status = pc.status(url3, include_txs=True)
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.CONFIRMING_SPEND
    assert status.ready == False
    assert status.balance == 400000
    assert status.deposit == 400000
    assert status.fee == 20000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 50000)
    assert status.expired == True
    assert status.deposit_txid
    assert status.spend_txid == str(bitcoin.Transaction.from_hex(status.transactions.refund_tx).hash)

    # Confirm refund
    bc.mock_confirm(status.spend_txid)

    # Sync
    pc.sync()

    # Check url3 properties
    status = pc.status(url3, include_txs=True)
    assert status.url == 'mock://test/' + status.deposit_txid
    assert status.state == statemachine.PaymentChannelState.CLOSED
    assert status.ready == False
    assert status.balance == 400000
    assert status.deposit == 400000
    assert status.fee == 20000
    assert status.creation_time > 0
    assert status.expiration_time == int(status.creation_time + 50000)
    assert status.expired == True
    assert status.deposit_txid
    assert status.spend_txid == str(bitcoin.Transaction.from_hex(status.transactions.refund_tx).hash)

    # Restore time.time()
    time.time = orig_time_time

    # Ensure all channels are closed
    for url in pc.list():
        assert pc.status(url).state == statemachine.PaymentChannelState.CLOSED
