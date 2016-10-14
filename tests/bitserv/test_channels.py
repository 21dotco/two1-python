"""Tests for payment channel functionality."""
import time
import codecs
import pytest
import collections
import multiprocessing

import two1.bitcoin.utils as utils
from two1.bitcoin import Script, Hash
from two1.bitcoin import PrivateKey
from two1.bitcoin import Transaction, TransactionInput, TransactionOutput
from two1.channels.statemachine import PaymentChannelRedeemScript
from two1.bitserv.payment_server import PaymentServer, PaymentServerError
from two1.bitserv.payment_server import PaymentChannelNotFoundError
from two1.bitserv.payment_server import TransactionVerificationError
from two1.bitserv.payment_server import BadTransactionError
from two1.bitserv.models import DatabaseSQLite3, ChannelSQLite3


class MockTwo1Wallet:

    """Wallet to mock two1 wallet functions in a test environment."""

    def __init__(self):
        """Initialize the mock wallet with a private key."""
        self._private_key = PrivateKey.from_random()
        self.testnet = False

    def get_payout_public_key(self, account='default'):
        """Return the public key associated with the private key."""
        return self._private_key.public_key

    def get_private_for_public(self, public_key):
        """Get this private key for this public key."""
        if public_key.to_hex() == self._private_key.public_key.to_hex():
            return self._private_key
        else:
            return None

    def create_deposit_tx(self, hash160):
        """Return a mocked deposit transaction."""
        utxo_script_sig = Script.build_p2pkh(self._private_key.public_key.hash160())
        inp = TransactionInput(
            outpoint=Hash('0' * 64), outpoint_index=0, script=utxo_script_sig, sequence_num=0xffffffff)
        out = TransactionOutput(value=120000, script=Script.build_p2sh(hash160))
        txn = Transaction(version=Transaction.DEFAULT_TRANSACTION_VERSION, inputs=[inp], outputs=[out], lock_time=0)
        txn.sign_input(
            input_index=0, hash_type=Transaction.SIG_HASH_ALL, private_key=self._private_key,
            sub_script=utxo_script_sig)
        return txn

    def create_payment_tx(self, deposit_tx, redeem_script, merchant_public_key,
                          customer_public_key, amount, fee):
        # Find P2SH output index in deposit_tx
        deposit_utxo_index = deposit_tx.output_index_for_address(redeem_script.hash160())

        # Look up deposit amount
        deposit_amount = deposit_tx.outputs[deposit_utxo_index].value - fee

        # Build unsigned payment transaction
        script_sig = Script()
        inp = TransactionInput(deposit_tx.hash, deposit_utxo_index, script_sig, 0xffffffff)
        out1 = TransactionOutput(amount, Script.build_p2pkh(merchant_public_key.hash160()))
        out2 = TransactionOutput(deposit_amount - amount, Script.build_p2pkh(customer_public_key.hash160()))
        payment_tx = Transaction(1, [inp], [out1, out2], 0x0)

        # Sign payment transaction
        public_key = redeem_script.customer_public_key
        private_key = self.get_private_for_public(public_key)
        sig = payment_tx.get_signature_for_input(0, Transaction.SIG_HASH_ALL, private_key, redeem_script)[0]

        # Update input script sig
        script_sig = Script(
            [sig.to_der() + utils.pack_compact_int(Transaction.SIG_HASH_ALL), 'OP_1', bytes(redeem_script)])
        payment_tx.inputs[0].script = script_sig

        return payment_tx


class MockBlockchain:

    def broadcast_tx(self, tx):
        pass

    def lookup_spend_txid(self, txid, output_index):
        return None

    def check_confirmed(self, txid, num_confirmations=1):
        return True


def mock_lookup_spent_txid(self, txid, output_index):
    return txid

###############################################################################

ClientVals = collections.namedtuple('ClientVals', ['deposit_tx', 'payment_tx', 'redeem_script'])
TEST_DEP_AMOUNT = 100000
TEST_DUST_AMOUNT = 1
TEST_PMT_AMOUNT = 5000
TEST_FEE_AMOUNT = 30000
TEST_EXPIRY = 86400
cust_wallet = MockTwo1Wallet()
merch_wallet = MockTwo1Wallet()
BAD_SIGNATURE = codecs.encode(cust_wallet._private_key.sign('fake').to_der(), 'hex_codec')
channel_server = PaymentServer(merch_wallet)
channel_server._blockchain = MockBlockchain()


def _create_client_txs():
    """Mock client transactions for opening a channel."""
    # Collect public keys
    expiration_time = int(time.time() + TEST_EXPIRY)
    customer_public_key = cust_wallet.get_payout_public_key()
    merchant_public_key = merch_wallet.get_payout_public_key()

    # Build redeem script
    redeem_script = PaymentChannelRedeemScript(
        merchant_public_key, customer_public_key, expiration_time)

    # Build deposit tx
    deposit_tx = cust_wallet.create_deposit_tx(redeem_script.hash160())

    # Build payment tx
    payment_tx = cust_wallet.create_payment_tx(
        deposit_tx, redeem_script, merchant_public_key,
        customer_public_key, TEST_PMT_AMOUNT, TEST_FEE_AMOUNT)

    return ClientVals(deposit_tx.to_hex(), payment_tx.to_hex(), redeem_script.to_hex())


def _create_client_payment(client, num):
    """Mock client transaction for a payment in a channel."""
    customer_public_key = cust_wallet.get_payout_public_key()
    merchant_public_key = merch_wallet.get_payout_public_key()
    deposit_tx = Transaction.from_hex(client.deposit_tx)
    redeem_script = PaymentChannelRedeemScript.from_bytes(codecs.decode(client.redeem_script, 'hex_codec'))
    return cust_wallet.create_payment_tx(
        deposit_tx, redeem_script, merchant_public_key, customer_public_key,
        TEST_PMT_AMOUNT * num, TEST_FEE_AMOUNT).to_hex()


def test_identify():
    """Test ability to identify a payment server."""
    channel_server._db = DatabaseSQLite3(':memory:', db_dir='')
    pc_config = channel_server.identify()
    merchant_public_key = pc_config['public_key']
    test_public_key = codecs.encode(
        merch_wallet._private_key.public_key.compressed_bytes,
        'hex_codec').decode('utf-8')
    assert merchant_public_key == test_public_key
    assert pc_config['version'] == channel_server.PROTOCOL_VERSION
    assert pc_config['zeroconf'] is False


def test_channel_server_open():
    """Test ability to open a payment channel."""
    channel_server._db = DatabaseSQLite3(':memory:', db_dir='')
    test_client = _create_client_txs()

    # Initialize the handshake and ensure that it returns successfully
    channel_server.open(test_client.deposit_tx, test_client.redeem_script)

    # Test for handshake failure when using the same refund twice
    with pytest.raises(PaymentServerError):
        channel_server.open(test_client.deposit_tx, test_client.redeem_script)


def test_receive_payment():
    """Test ability to receive a payment within a channel."""
    channel_server._db = DatabaseSQLite3(':memory:', db_dir='')
    test_client = _create_client_txs()

    # Test that payment receipt fails when no channel exists
    with pytest.raises(PaymentChannelNotFoundError):
        channel_server.receive_payment('fake', test_client.payment_tx)

    # Initiate and complete the payment channel handshake
    deposit_txid = channel_server.open(test_client.deposit_tx, test_client.redeem_script)

    # Test that payment receipt succeeds
    channel_server.receive_payment(deposit_txid, test_client.payment_tx)

    # Test that payment receipt fails with a duplicate payment
    with pytest.raises(PaymentServerError):
        channel_server.receive_payment(deposit_txid, test_client.payment_tx)


def test_redeem_payment():
    """Test ability to redeem a payment made within a channel."""
    channel_server._db = DatabaseSQLite3(':memory:', db_dir='')
    test_client = _create_client_txs()

    # Test that payment redeem fails when no channel exists
    with pytest.raises(PaymentChannelNotFoundError):
        channel_server.redeem('fake')

    # Test that payment redeem succeeds
    deposit_txid = channel_server.open(test_client.deposit_tx, test_client.redeem_script)
    payment_txid = channel_server.receive_payment(deposit_txid, test_client.payment_tx)

    amount = channel_server.redeem(payment_txid)
    assert amount == TEST_PMT_AMOUNT

    # Test that payment redeem fails with a duplicate payment
    with pytest.raises(PaymentServerError):
        channel_server.redeem(payment_txid)


def test_status_close_channel():
    """Test ability to get a channel's status and close it."""
    channel_server._db = DatabaseSQLite3(':memory:', db_dir='')
    test_client = _create_client_txs()

    # Test that channel close fails when no channel exists
    with pytest.raises(PaymentChannelNotFoundError):
        channel_server.close('fake', BAD_SIGNATURE)

    # Open the channel and make a payment
    deposit_txid = channel_server.open(test_client.deposit_tx, test_client.redeem_script)
    payment_txid = channel_server.receive_payment(deposit_txid, test_client.payment_tx)
    channel_server.redeem(payment_txid)

    # Test that channel close fails without a valid signature
    with pytest.raises(TransactionVerificationError):
        closed = channel_server.close(deposit_txid, BAD_SIGNATURE)

    # Test that channel close succeeds
    good_signature = codecs.encode(cust_wallet._private_key.sign(deposit_txid).to_der(), 'hex_codec')
    closed = channel_server.close(deposit_txid, good_signature)
    assert closed


def test_channel_sync(monkeypatch):
    """Test ability to sync the status of all channels."""
    channel_server._db = DatabaseSQLite3(':memory:', db_dir='')

    # Seed the database with activity in Channel A
    test_client_a = _create_client_txs()
    deposit_txid_a = channel_server.open(test_client_a.deposit_tx, test_client_a.redeem_script)
    payment_txid = channel_server.receive_payment(deposit_txid_a, test_client_a.payment_tx)
    amount = channel_server.redeem(payment_txid)
    assert amount == TEST_PMT_AMOUNT

    # Seed the database with activity in Channel B
    cust_wallet._private_key = PrivateKey.from_random()
    test_client_b = _create_client_txs()
    deposit_txid_b = channel_server.open(test_client_b.deposit_tx, test_client_b.redeem_script)
    payment_txid = channel_server.receive_payment(deposit_txid_b, test_client_b.payment_tx)
    amount = channel_server.redeem(payment_txid)
    payment_tx1 = _create_client_payment(test_client_b, 2)
    payment_tx2 = _create_client_payment(test_client_b, 3)
    payment_tx3 = _create_client_payment(test_client_b, 4)
    payment_txid1 = channel_server.receive_payment(deposit_txid_b, payment_tx1)
    payment_txid2 = channel_server.receive_payment(deposit_txid_b, payment_tx2)
    payment_txid3 = channel_server.receive_payment(deposit_txid_b, payment_tx3)
    amount1 = channel_server.redeem(payment_txid1)
    amount2 = channel_server.redeem(payment_txid3)
    amount3 = channel_server.redeem(payment_txid2)
    assert amount1 == TEST_PMT_AMOUNT
    assert amount2 == TEST_PMT_AMOUNT
    assert amount3 == TEST_PMT_AMOUNT

    # Both channels should be `ready` since our channel is zeroconf by default
    channels = channel_server._db.pc.lookup()
    assert channels, 'Channel lookup with no args should return a list of all channels.'
    for channel in channels:
        assert channel.state == ChannelSQLite3.READY, 'Channel should be READY.'

    # Change Channel A to `confirming` for testing purposes
    channel_server._db.pc.update_state(deposit_txid_a, ChannelSQLite3.CONFIRMING)
    test_state = channel_server._db.pc.lookup(deposit_txid_a).state
    assert test_state == ChannelSQLite3.CONFIRMING, 'Channel should be CONFIRMING'

    # Change Channel B's expiration to be very close to allowable expiration
    new_expiry = int(time.time() + 3600)
    update = 'UPDATE payment_channel SET expires_at=? WHERE deposit_txid=?'
    channel_server._db.pc.c.execute(update, (new_expiry, deposit_txid_b))
    channel_server._db.pc.c.connection.commit()
    test_expiry = channel_server._db.pc.lookup(deposit_txid_b).expires_at
    assert test_expiry == new_expiry, 'Channel should closing soon.'

    # Sync all of the server's payment channels
    channel_server.sync()

    # Test that Channel A is `ready` after a sync
    test_state = channel_server._db.pc.lookup(deposit_txid_a).state
    assert test_state == ChannelSQLite3.READY, 'Channel should be READY'

    # Test that Channel B is `closed` after a sync
    test_state = channel_server._db.pc.lookup(deposit_txid_b).state
    assert test_state == ChannelSQLite3.CLOSED, 'Channel should be CLOSED'

    # Test that Channel B payment is fully signed after a sync
    test_payment = channel_server._db.pc.lookup(deposit_txid_b).payment_tx
    goodsig_1 = Script.validate_template(test_payment.inputs[0].script, [bytes, bytes, 'OP_1', bytes])
    goodsig_true = Script.validate_template(test_payment.inputs[0].script, [bytes, bytes, 'OP_TRUE', bytes])
    assert goodsig_1 or goodsig_true, 'Payment should be in a fully signed format'

    # Test that Channel A remains `ready` after another sync
    channel_server.sync()
    test_state = channel_server._db.pc.lookup(deposit_txid_a).state
    assert test_state == ChannelSQLite3.READY, 'Channel should be READY'

    # Modify `lookup_spend_txid` to return a txid, as if the tx were spent
    monkeypatch.setattr(MockBlockchain, 'lookup_spend_txid', mock_lookup_spent_txid)

    # Test that Channel A is `closed` after a sync where it finds a spent txid
    channel_server.sync()
    test_state = channel_server._db.pc.lookup(deposit_txid_a).state
    assert test_state == ChannelSQLite3.CLOSED, 'Channel should be CLOSED'


def test_channel_low_balance_message():
    """Test that the channel server returns a useful error when the balance is low."""
    channel_server._db = DatabaseSQLite3(':memory:', db_dir='')
    test_client = _create_client_txs()

    # Open the channel and make a payment
    deposit_txid = channel_server.open(test_client.deposit_tx, test_client.redeem_script)
    payment_txid = channel_server.receive_payment(deposit_txid, test_client.payment_tx)
    channel_server.redeem(payment_txid)

    # Create a payment that almost completely drains the channel
    payment_tx2 = _create_client_payment(test_client, 17)
    payment_txid2 = channel_server.receive_payment(deposit_txid, payment_tx2)
    channel_server.redeem(payment_txid2)

    # Make a payment that spends more than the remaining channel balance
    payment_tx3 = _create_client_payment(test_client, 18)
    with pytest.raises(BadTransactionError) as exc:
        channel_server.receive_payment(deposit_txid, payment_tx3)

    assert 'Payment channel balance' in str(exc)

    # Test that channel close succeeds
    good_signature = codecs.encode(cust_wallet._private_key.sign(deposit_txid).to_der(), 'hex_codec')
    closed = channel_server.close(deposit_txid, good_signature)
    assert closed


def test_channel_redeem_race_condition():
    """Test ability lock multiprocess redeems."""
    # Clear test database
    multiprocess_db = '/tmp/bitserv_test.sqlite3'
    with open(multiprocess_db, 'w') as f:
        f.write('')

    # Initialize test vectors
    channel_server._db = DatabaseSQLite3(multiprocess_db)
    test_client = _create_client_txs()
    deposit_txid = channel_server.open(test_client.deposit_tx, test_client.redeem_script)
    payment_txid = channel_server.receive_payment(deposit_txid, test_client.payment_tx)

    # Cache channel result for later
    channel = channel_server._db.pc.lookup(deposit_txid)

    # This is a function that takes a long time
    def delayed_pc_lookup(deposit_txid):
        time.sleep(0.5)
        return channel

    # This is the normal function
    def normal_pc_lookup(deposit_txid):
        return channel

    # This function is called between the first lookup and the final record update
    # We make sure this function takes extra long the first time its called
    # in order to expose the race condition
    channel_server._db.pc.lookup = delayed_pc_lookup

    # Start the first redeem in its own process and allow time to begin
    p = multiprocessing.Process(target=channel_server.redeem, args=(payment_txid,))
    p.start()
    time.sleep(0.1)

    # After starting the first redeem, reset the function to take a normal amount of time
    channel_server._db.pc.lookup = normal_pc_lookup

    # To test the race, this redeem is called while the other redeem is still in-process
    # Because this call makes it to the final database update first, it should be successful
    channel_server.redeem(payment_txid)

    # The multiprocess redeem is intentionally made slow, and will finish after the redeem above
    # Because of this, the multiprocess redeem should throw and exception and exit with an error
    p.join()
    assert p.exitcode == 1
