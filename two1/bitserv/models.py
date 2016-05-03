"""This module provides data management for payment servers."""
import os
import time
import sqlite3
import collections
from two1.bitcoin import Transaction

Channel = collections.namedtuple('Channel', [
    'deposit_txid', 'state', 'deposit_tx', 'payment_tx', 'merchant_pubkey',
    'created_at', 'expires_at', 'amount', 'last_payment_amount'])
Payment = collections.namedtuple('Payment', [
    'payment_txid', 'payment_tx', 'amount', 'is_redeemed', 'deposit_txid'])

###############################################################################
# Payment Channel Models                                                      #
###############################################################################

# *************************** Base Data Models ****************************** #


class ChannelDataManager:

    """Manages payment channel data for specific channels and payments."""

    def __init__(self):
        """Provides an interface to the two payment channel data models.

        A ChannelDataManager should expose an attribute named `pc`, which is
        an instance of a ChannelDatabase, as well as an attribute named `pmt`,
        which is an instance of a PaymentDatabase. The PaymentServer relies on
        the ChannelDataManager to maintain its state.
        """
        pass


class ChannelDatabase:

    """Model that contains all payment channels."""

    def __init__(self):
        pass

    def create(self, deposit_tx, merch_pubkey, amount, expiration):
        """Create a payment channel entry.

        Args:
            deposit_tx (two1.bitcoin.Transaction): initial deposit used to
                open the payment channel.
            merch_pubkey (str): the merchant public key used in the channel.
            amount (int): the opening balance of the payment channel.
            expiration (int): expiration timestamp in UNIX Epoch time.
        """
        raise NotImplementedError()

    def lookup(self, deposit_txid=None):
        """Look up a payment channel entry by deposit txid.

        Args:
            deposit_txid (str): optional argument to find a single channel or
                query for all channels (in the case of a sync).
        Returns:
            Channel (collections.namedtuple): named tuple as defined above,
                with `deposit_tx` and `payment_tx` as Transaction objects.
        """
        raise NotImplementedError()

    def update_payment(self, deposit_txid, payment_tx, payment_amount):
        """Update a payment channel with a new payment transaction.

        Args:
            deposit_txid (str): deposit txid used to identify the channel.
            payment_tx (two1.bitcoin.Transaction): payment transaction made
                within the channel.
            payment_amount (int): incremental payment amount of the tx.
        """
        raise NotImplementedError()

    def update_state(self, deposit_txid, new_state):
        """Update payment channel state.

        Args:
            deposit_txid (str): deposit txid used to identify the channel.
            new_state (str): new state used for updating the channel.
        """
        raise NotImplementedError()


class PaymentDatabase:

    """Model that contains all payments made within channels."""

    def __init__(self):
        pass

    def create(self, deposit_txid, payment_tx, amount):
        """Create a payment entry.

        Args:
            deposit_txid (str): deposit txid used to identify the channel.
            payment_tx (two1.bitcoin.Transaction): payment transaction made
                within the channel.
            amount (int): the opening balance of the payment channel.
            payment_amount (int): incremental payment amount of the tx.
        """
        raise NotImplementedError()

    def lookup(self, payment_txid):
        """Look up a payment entry by payment txid.

        Args:
            payment_txid (str): payment txid used to identify the payment.
        Returns:
            Payment (collections.namedtuple): named tuple as defined above,
                with `payment_tx` as a Transaction object.
        """
        raise NotImplementedError()

    def redeem(self, payment_txid):
        """Update payment entry to be redeemed.

        Args:
            payment_txid (str): payment txid used to identify the payment.
        """
        raise NotImplementedError()


# *************************** Django Data ORM ****************************** #


class DatabaseDjango(ChannelDataManager):

    """Payment channel data bindings for django models."""

    def __init__(self, Channel, Payment):
        self.pc = ChannelDjango(Channel)
        self.pmt = PaymentDjango(Payment)


class ChannelDjango(ChannelDatabase):

    """Django binding for the payment channel model."""

    CONFIRMING = 'confirming'
    READY = 'ready'
    CLOSED = 'closed'

    def __init__(self, ChannelModel):
        """Initialize the channel data handler with a Channel django model."""
        self.Channel = ChannelModel

    def create(self, deposit_tx, merch_pubkey, amount, expiration):
        """Create a payment channel entry."""
        ch = self.Channel(deposit_txid=str(deposit_tx.hash), state=ChannelDjango.CONFIRMING,
                          deposit_tx=deposit_tx.to_hex(), merchant_pubkey=merch_pubkey,
                          expires_at=expiration, amount=amount)
        ch.save()

    def lookup(self, deposit_txid=None):
        """Look up a payment channel entry by deposit txid."""
        # Check whether to query a single channel or all
        if not deposit_txid:
            query = self.Channel.objects.all()
        else:
            try:
                query = [self.Channel.objects.get(deposit_txid=deposit_txid)]
            except self.Channel.DoesNotExist:
                query = []
        if not len(query) or not query[0]:
            return None

        # Collect all records as a list of Channels
        records = []
        for rec in query:
            deposit_tx = Transaction.from_hex(rec.deposit_tx) if rec.deposit_tx else None
            payment_tx = Transaction.from_hex(rec.payment_tx) if rec.payment_tx else None
            records.append(Channel(rec.deposit_txid, rec.state, deposit_tx, payment_tx,
                                   rec.merchant_pubkey, rec.created_at, rec.expires_at,
                                   rec.amount, rec.last_payment_amount))

        # Return a single record or list of records
        return records if len(records) > 1 else records[0]

    def update_payment(self, deposit_txid, payment_tx, payment_amount):
        """Update a payment channel with a new payment transaction."""
        self.Channel.objects.filter(deposit_txid=deposit_txid).update(
            payment_tx=payment_tx.to_hex(), last_payment_amount=payment_amount)

    def update_state(self, deposit_txid, new_state):
        """Update payment channel state."""
        self.Channel.objects.filter(deposit_txid=deposit_txid).update(state=new_state)


class PaymentDjango(ChannelDatabase):

    """Django binding for the payment model."""

    def __init__(self, PaymentModel):
        """Initialize the payment data handler with a Payment django model."""
        self.Payment = PaymentModel

    def create(self, deposit_txid, payment_tx, amount):
        """Create a payment entry."""
        pmt = self.Payment(payment_txid=str(payment_tx.hash), amount=amount,
                           payment_tx=payment_tx.to_hex(), deposit_txid=deposit_txid)
        pmt.save()

    def lookup(self, payment_txid):
        """Look up a payment entry by deposit txid."""
        try:
            rec = self.Payment.objects.get(payment_txid=payment_txid)
        except self.Payment.DoesNotExist:
            return None
        return Payment(rec.payment_txid, Transaction.from_hex(rec.payment_tx),
                       rec.amount, rec.is_redeemed, rec.deposit_txid)

    def redeem(self, payment_txid):
        """Update payment entry to be redeemed."""
        self.Payment.objects.filter(payment_txid=payment_txid).update(is_redeemed=True)


# *************************** Default SQLite3 ****************************** #


class DatabaseSQLite3(ChannelDataManager):

    """Default payment channel data bindings when no data service is provided."""

    DEFAULT_PAYMENT_DB_DIR = os.path.expanduser('~/.two1/payment/')
    DEFAULT_PAYMENT_DB_PATH = 'payment.sqlite3'

    def __init__(self, db=None, db_dir=None):
        if db_dir is None:
            db_dir = DatabaseSQLite3.DEFAULT_PAYMENT_DB_DIR
        if db is None:
            db = DatabaseSQLite3.DEFAULT_PAYMENT_DB_PATH
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        self.connection = sqlite3.connect(os.path.join(db_dir, db), check_same_thread=False)
        self.c = self.connection.cursor()
        self.pc = ChannelSQLite3(self)
        self.pmt = PaymentSQLite3(self)


class ChannelSQLite3(ChannelDatabase):

    """SQLite3 binding for the payment channel model."""

    CONFIRMING = 'confirming'
    READY = 'ready'
    CLOSED = 'closed'

    def __init__(self, db):
        """Instantiate SQLite3 for storing channel transaction data."""
        self.c = db.c
        self.connection = db.connection
        self.c.execute("CREATE TABLE IF NOT EXISTS 'payment_channel' "
                       "(deposit_txid text unique, state text, "
                       "deposit_tx text, payment_tx text, "
                       "merchant_pubkey text, created_at timestamp, "
                       "expires_at timestamp, amount integer, "
                       "last_payment_amount integer)")

    def create(self, deposit_tx, merch_pubkey, amount, expiration):
        """Create a payment channel entry."""
        insert = 'INSERT INTO payment_channel VALUES (?' + ',?' * 8 + ')'
        self.c.execute(insert, (str(deposit_tx.hash), ChannelSQLite3.CONFIRMING,
                                deposit_tx.to_hex(), None, merch_pubkey,
                                time.time(), expiration, amount, 0))
        self.connection.commit()

    def lookup(self, deposit_txid=None):
        """Look up a payment channel entry by deposit txid."""
        # Check whether to query a single channel or all
        if not deposit_txid:
            self.c.execute('SELECT * FROM payment_channel')
            query = self.c.fetchall()
        else:
            select = 'SELECT * FROM payment_channel WHERE deposit_txid=?'
            self.c.execute(select, (deposit_txid,))
            query = [self.c.fetchone()]
        if not len(query) or not query[0]:
            return None

        # Collect all records as a list of Channels
        records = []
        for rec in query:
            record = list(rec)
            record[2] = Transaction.from_hex(record[2]) if record[2] else None
            record[3] = Transaction.from_hex(record[3]) if record[3] else None
            records.append(Channel(*record))

        # Return a single record or list of records
        return records if len(records) > 1 else records[0]

    def update_payment(self, deposit_txid, payment_tx, payment_amount):
        """Update a payment channel with a new payment transaction."""
        update = ('UPDATE payment_channel SET payment_tx=?,'
                  'last_payment_amount=? WHERE deposit_txid=?')
        self.c.execute(update, (payment_tx.to_hex(), payment_amount, deposit_txid))
        self.connection.commit()

    def update_state(self, deposit_txid, new_state):
        """Update payment channel state."""
        update = 'UPDATE payment_channel SET state=? WHERE deposit_txid=?'
        self.c.execute(update, (new_state, deposit_txid))
        self.connection.commit()


class PaymentSQLite3(PaymentDatabase):

    """SQLite3 binding for the payment model."""

    NOT_REDEEMED = 0
    WAS_REDEEMED = 1

    def __init__(self, db):
        """Instantiate SQLite3 for storing channel payment data."""
        self.c = db.c
        self.connection = db.connection
        self.c.execute("CREATE TABLE IF NOT EXISTS 'payment_channel_spend' "
                       "(payment_txid text unique, payment_tx text, "
                       "amount integer, is_redeemed integer, "
                       "deposit_txid text)")

    def create(self, deposit_txid, payment_tx, amount):
        """Create a payment entry."""
        insert = 'INSERT INTO payment_channel_spend VALUES (?,?,?,?,?)'
        self.c.execute(insert, (str(payment_tx.hash), payment_tx.to_hex(), amount,
                                PaymentSQLite3.NOT_REDEEMED, deposit_txid))
        self.connection.commit()

    def lookup(self, payment_txid):
        """Look up a payment entry by deposit txid."""
        select = 'SELECT * FROM payment_channel_spend WHERE payment_txid=?'
        self.c.execute(select, (payment_txid,))
        rv = self.c.fetchone()
        if rv is None:
            return rv
        channel = list(rv)
        channel[1] = Transaction.from_hex(channel[1])
        channel[3] = channel[3] == PaymentSQLite3.WAS_REDEEMED
        return Payment(*channel)

    def redeem(self, payment_txid):
        """Update payment entry to be redeemed."""
        update = ('UPDATE payment_channel_spend SET is_redeemed=? '
                  'WHERE payment_txid=?')
        self.c.execute(update, (PaymentSQLite3.WAS_REDEEMED, payment_txid))
        self.connection.commit()


##############################################################################
# On-Chain Transaction Models                                                #
##############################################################################

# *************************** Base Data Models ****************************** #


class OnChainDatabase:

    """Model that contains all on-chain payment transactions."""

    def __init__(self):
        pass

    def create(txid):
        """Create a transaction entry."""
        pass

    def lookup(txid):
        """Look up a transaction entry."""
        pass

    def delete(txid):
        """Delete a transaction entry."""
        pass

# *************************** Django Data ORM ****************************** #


class OnChainDjango(OnChainDatabase):

    """Django binding for the on-chain transaction model."""

    def __init__(self, BlockchainTransaction):
        self.BlockchainTransaction = BlockchainTransaction

    def create(self, txid, amount):
        """Create a transaction entry."""
        bt = self.BlockchainTransaction(txid=txid, amount=amount)
        bt.save()
        return True

    def lookup(self, txid):
        """Look up a transaction entry."""
        try:
            rv = self.BlockchainTransaction.objects.get(txid=txid)
            return {'txid': rv.txid, 'amount': rv.amount}
        except self.BlockchainTransaction.DoesNotExist:
            return None

    def delete(self, txid):
        """Delete a transaction entry."""
        try:
            txn = self.BlockchainTransaction.objects.get(txid=txid)
            txn.delete()
        except self.BlockchainTransaction.DoesNotExist:
            return None

# *************************** Default SQLite3 ****************************** #


class OnChainSQLite3(OnChainDatabase):

    """SQLite3 binding for the on-chain transaction model."""

    DEFAULT_PAYMENT_DB_DIR = os.path.expanduser('~/.two1/payment/')
    DEFAULT_PAYMENT_DB_PATH = 'payment.sqlite3'

    def __init__(self, db=None, db_dir=None):
        """Instantiate SQLite3 for storing on chain transaction data."""
        if db_dir is None:
            db_dir = OnChainSQLite3.DEFAULT_PAYMENT_DB_DIR
        if db is None:
            db = OnChainSQLite3.DEFAULT_PAYMENT_DB_PATH
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
        self.connection = sqlite3.connect(os.path.join(db_dir, db), check_same_thread=False)
        self.c = self.connection.cursor()
        self.c.execute("CREATE TABLE IF NOT EXISTS 'payment_onchain' (txid text, amount integer)")

    def create(self, txid, amount):
        """Create a transaction entry."""
        insert = 'INSERT INTO payment_onchain VALUES (?, ?)'
        self.c.execute(insert, (txid, amount))
        self.connection.commit()
        return {'txid': txid, 'amount': amount}

    def lookup(self, txid):
        """Look up a transaction entry."""
        select = 'SELECT txid, amount FROM payment_onchain WHERE txid=?'
        self.c.execute(select, (txid,))
        rv = self.c.fetchone()
        if rv is None:
            return rv
        return {'txid': rv[0], 'amount': rv[1]}

    def delete(self, txid):
        """Delete a transaction entry."""
        delete = 'DELETE FROM payment_onchain WHERE txid=?'
        self.c.execute(delete, (txid,))
        self.connection.commit()
