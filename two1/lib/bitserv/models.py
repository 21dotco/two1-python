""""""
import time
import codecs
import sqlite3
from two1.lib.bitcoin import Transaction


###############################################################################
# Payment Channel Models                                                      #
###############################################################################

# *************************** Base Data Models ****************************** #

class ChannelError(Exception):
    pass


class ModelNotFound(ChannelError):
    pass


class DuplicateRequestError(ChannelError):
    pass


class InvalidPaymentError(ChannelError):
    pass


class ChannelDatabase:

    def __init__(self):
        pass

    def create(self, refund_tx, merch_pubkey):
        raise NotImplementedError()

    def lookup(self, deposit_txid):
        raise NotImplementedError()

    def update_deposit(self, deposit_txid, deposit_tx, amount):
        raise NotImplementedError()

    def update_payment(self, deposit_txid, payment_tx, pmt_amt):
        raise NotImplementedError()

    def delete(self, deposit_txid):
        raise NotImplementedError()


class PaymentDatabase:

    def __init__(self):
        pass

    def create(self, payment_tx):
        raise NotImplementedError()

    def lookup(self, payment_txid):
        raise NotImplementedError()

    def redeem(self, payment_txid):
        raise NotImplementedError()


# *************************** Django Data ORM ****************************** #


class DatabaseDjango:

    """Payment channel data bindings for django models."""

    def __init__(self, Channel, Payment):
        self.Channel = ChannelDjango(Channel)
        self.Payment = PaymentDjango(Payment)


class ChannelDjango(ChannelDatabase):

    def __init__(self, Channel):
        self.Channel = Channel

    def create(self, refund_tx, merch_pubkey):
        """Create a payment channel entry."""
        deposit_txid = str(refund_tx.inputs[0].outpoint)
        state = 'opening'
        now = time.time()
        expiry = refund_tx.lock_time
        mp = codecs.encode(merch_pubkey.compressed_bytes, 'hex_codec').decode()
        self.Channel.create(deposit_txid=deposit_txid, state=state,
                            refund_tx=refund_tx.to_hex(), merchant_pubkey=mp,
                            expires_at=expiry)
        return True

    def lookup(self, deposit_txid):
        """Look up a payment channel entry by deposit txid."""
        rv = self.Channel.objects.get(deposit_txid=deposit_txid)
        deposit_tx = Transaction.from_hex(rv.deposit_tx) if rv.deposit_tx else None
        payment_tx = Transaction.from_hex(rv.payment_tx) if rv.payment_tx else None
        refund_tx = Transaction.from_hex(rv.refund_tx) if rv.refund_tx else None
        return {'deposit_txid': rv.deposit_txid, 'state': rv.state,
                'deposit_tx': deposit_tx, 'payment_tx': payment_tx,
                'refund_tx': refund_tx, 'merchant_pubkey': rv.merchant_pubkey,
                'created_at': rv.created_at, 'expires_at': rv.expires_at,
                'amount': rv.amount, 'last_payment_amount': rv.last_payment_amount}

    def update_deposit(self, deposit_txid, deposit_tx, amount):
        """Update a payment channel with the deposit transaction."""
        # Make sure there isn't already a deposit in this channel
        rv = self.Channel.objects.get(deposit_txid=deposit_txid)
        if rv.deposit is not None:
            raise DuplicateRequestError()
        # Update the channel with the new deposit
        rv.update(deposit_tx=deposit_tx.to_hex(), amount=amount)
        return True

    def update_payment(self, deposit_txid, payment_tx, pmt_amt):
        """Update a payment channel with a new payment transaction."""
        self.Channel.objects.get(deposit_txid=deposit_txid).update(
            payment_tx=payment_tx, last_payment_amount=pmt_amt)
        return True

    def update_state(self, deposit_txid, new_state):
        """Update payment channel state."""
        self.Channel.objects.get(deposit_txid=deposit_txid).update(state=new_state)
        return True


class PaymentDjango(ChannelDatabase):

    def __init__(self, Payment):
        self.Payment = Payment

    def create(self, deposit_txid, payment_tx, amount):
        """Create a payment entry."""
        self.Payment.create(payment_txid=payment_txid, amount=amount,
                            payment_tx=payment_tx.to_hex(),
                            deposit_txid=deposit_txid)
        return True

    def lookup(self, payment_txid):
        """Look up a payment entry by deposit txid."""
        rv = self.Payment.objects.get(payment_txid=payment_txid)
        return {'payment_txid': rv.payment_txid,
                'payment_tx': Transaction.from_hex(rv.payment_tx),
                'amount': rv.amount, 'is_redeemed': rv.is_redeemed,
                'deposit_txid': rv.deposit_txid}

    def redeem(self, payment_txid):
        """Update payment entry to be redeemed."""
        self.Payment.objects.get(payment_txid=txid).update(is_redeemed=True)
        return True


class DatabaseSQLite3:

    """Default payment channel data bindings when no data service is provided."""

    def __init__(self, db='payment.sqlite3'):
        self.connection = sqlite3.connect(db, check_same_thread=False)
        self.c = self.connection.cursor()
        self.pc = ChannelSQLite3(self)
        self.pmt = PaymentSQLite3(self)


# *************************** Default SQLite3 ****************************** #

class ChannelSQLite3(ChannelDatabase):

    def __init__(self, db):
        """Instantiate SQLite3 for storing channel transaction data."""
        self.c = db.c
        self.connection = db.connection
        self.c.execute("CREATE TABLE IF NOT EXISTS 'payment_channel' "
                       "(deposit_txid text unique, state text,"
                       "deposit_tx text, payment_tx text, refund_tx text, "
                       "merchant_pubkey text, created_at timestamp, "
                       "expires_at timestamp, amount integer, "
                       "last_payment_amount integer)")

    def create(self, refund_tx, merch_pubkey):
        """Create a payment channel entry."""
        deposit_txid = str(refund_tx.inputs[0].outpoint)
        state = 'opening'
        now = time.time()
        expiry = refund_tx.lock_time
        mp = codecs.encode(merch_pubkey.compressed_bytes, 'hex_codec').decode()
        insert = 'INSERT INTO payment_channel VALUES (?' + ',?' * 9 + ')'
        self.c.execute(insert, (deposit_txid, state, None, None,
                                refund_tx.to_hex(), mp, now, expiry, 0, 0))
        self.connection.commit()
        return True

    def lookup(self, deposit_txid):
        """Look up a payment channel entry by deposit txid."""
        select = 'SELECT * FROM payment_channel WHERE deposit_txid=?'
        self.c.execute(select, (deposit_txid,))
        rv = self.c.fetchone()
        if rv is None:
            raise ModelNotFound()
        deposit_tx = Transaction.from_hex(rv[2]) if rv[2] else None
        payment_tx = Transaction.from_hex(rv[3]) if rv[3] else None
        refund_tx = Transaction.from_hex(rv[4]) if rv[4] else None
        return {'deposit_txid': rv[0], 'state': rv[1],
                'deposit_tx': deposit_tx, 'payment_tx': payment_tx,
                'refund_tx': refund_tx, 'merchant_pubkey': rv[5],
                'created_at': rv[6], 'expires_at': rv[7], 'amount': rv[8],
                'last_payment_amount': rv[9]}

    def update_deposit(self, deposit_txid, deposit_tx, amount):
        """Update a payment channel with the deposit transaction."""
        # Make sure there isn't already a deposit in this channel
        select = 'SELECT deposit_tx FROM payment_channel WHERE deposit_txid=?'
        self.c.execute(select, (deposit_txid,))
        deposit = self.c.fetchone()[0]
        if deposit is not None:
            raise DuplicateRequestError()
        # Update the channel with the new deposit
        update = ('UPDATE payment_channel SET deposit_tx=?, amount=? '
                  'WHERE deposit_txid=?')
        self.c.execute(update, (deposit_tx.to_hex(), amount, deposit_txid))
        self.connection.commit()
        return True

    def update_payment(self, deposit_txid, payment_tx, pmt_amt):
        """Update a payment channel with a new payment transaction."""
        update = ('UPDATE payment_channel SET payment_tx=?,'
                  'last_payment_amount=? WHERE deposit_txid=?')
        self.c.execute(update, (payment_tx.to_hex(), pmt_amt, deposit_txid))
        return True

    def update_state(self, deposit_txid, new_state):
        """Update payment channel state."""
        update = 'UPDATE payment_channel SET state=? WHERE deposit_txid=?'
        self.c.execute(update, (new_state, deposit_txid))
        self.connection.commit()
        return True


class PaymentSQLite3(PaymentDatabase):

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
        self.c.execute(insert, (str(payment_tx.hash), payment_tx.to_hex(),
                                amount, 0, deposit_txid))
        self.connection.commit()
        return True

    def lookup(self, payment_txid):
        """Look up a payment entry by deposit txid."""
        select = 'SELECT * FROM payment_channel_spend WHERE payment_txid=?'
        self.c.execute(select, (payment_txid,))
        rv = self.c.fetchone()
        if rv is None:
            raise ModelNotFound()
        return {'payment_txid': rv[0],
                'payment_tx': Transaction.from_hex(rv[1]),
                'amount': rv[2], 'is_redeemed': (rv[3] == 1),
                'deposit_txid': rv[4]}

    def redeem(self, payment_txid):
        """Update payment entry to be redeemed."""
        update = ('UPDATE payment_channel_spend SET is_redeemed=? '
                  'WHERE payment_txid=?')
        self.c.execute(update, (1, payment_txid))
        self.connection.commit()
        return True


##############################################################################
# On-Chain Transaction Models                                                #
##############################################################################

# *************************** Base Data Models ****************************** #

class OnChainError(Exception):
    pass


class OnChainDatabase:

    def __init__(self):
        pass

    def create(txid):
        pass

    def lookup(txid):
        pass

    def delete(txid):
        pass

# *************************** Django Data ORM ****************************** #


class OnChainDjango(OnChainDatabase):

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

    def __init__(self, db='payment.sqlite3'):
        """Instantiate SQLite3 for storing on chain transaction data."""
        self.connection = sqlite3.connect(db, check_same_thread=False)
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
