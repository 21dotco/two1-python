"""Provides persistent storage and retrieval of payment channel state."""
import os
import fcntl
import sqlite3
import threading

import two1.bitcoin as bitcoin

from .statemachine import PaymentChannelModel, PaymentChannelState


class DatabaseBase:
    """Base class for a Database interface."""

    def create(self, model):
        """Create a new payment channel in the database.

        Args:
            model (PaymentChannelModel): Payment channel state model.

        """
        raise NotImplementedError()

    def read(self, url):
        """Read a payment channel from the database.

        Args:
            url (str): Channel URL (primary key).

        Returns:
            PaymentChannelModel: Payment channel state model.

        """
        raise NotImplementedError()

    def update(self, model):
        """Update a payment channel in the database.

        Args:
            model (PaymentChannelModel): Payment channel state model.

        """
        raise NotImplementedError()

    def list(self):
        """List all payment channels urls in database.

        Returns:
            list: List of urls (str).

        """
        raise NotImplementedError()

    @property
    def lock(self):
        """Get a database lock."""
        raise NotImplementedError()

    def __enter__(self):
        """Enter a database transaction session."""
        raise NotImplementedError()

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit a database transaction session."""
        raise NotImplementedError()


class Sqlite3Database(DatabaseBase):
    """Sqlite3 implementation of the database interface."""

    def __init__(self, db_path):
        """Create a new Sqlite3Database instance.

        Args:
            db_path (str): Database path.

        Returns:
            Sqlite3Database: Instance of Sqlite3Database.

        """
        self._db_path = db_path

        # Create the channels table if it doesn't exist
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        with self._conn:
            self._conn.execute("CREATE TABLE IF NOT EXISTS "
                               "channels ("
                               "url VARCHAR NOT NULL PRIMARY KEY, "
                               "state VARCHAR(18), "
                               "creation_time FLOAT, "
                               "deposit_tx VARCHAR, "
                               "refund_tx VARCHAR, "
                               "payment_tx VARCHAR, "
                               "spend_tx VARCHAR, "
                               "spend_txid VARCHAR, "
                               "min_output_amount INTEGER, "
                               "CONSTRAINT state CHECK (state IN ('OPENING', 'CONFIRMING_DEPOSIT', 'READY', 'OUTSTANDING', 'CONFIRMING_SPEND', 'CLOSED'))"  # nopep8
                               ");")

        if db_path == ":memory:":
            self._lock = threading.Lock()
        else:
            self._lock = Sqlite3DatabaseLock(db_path)

    @staticmethod
    def _model_to_sqlite(model):
        """Convert a PaymentChannelModel into tuple of SQLite values.

        Args:
            model (PaymentChannelModel): Payment channel state model.

        Returns:
            tuple: Tuple of SQLite values representing a PaymentChannelModel.

        """
        url = model.url
        state = model.state.name
        creation_time = model.creation_time
        deposit_tx = model.deposit_tx.to_hex() if model.deposit_tx else None
        refund_tx = model.refund_tx.to_hex() if model.refund_tx else None
        payment_tx = model.payment_tx.to_hex() if model.payment_tx else None
        spend_tx = model.spend_tx.to_hex() if model.spend_tx else None
        spend_txid = model.spend_txid
        min_output_amount = model.min_output_amount

        return (url, state, creation_time, deposit_tx, refund_tx, payment_tx, spend_tx, spend_txid, min_output_amount)

    @staticmethod
    def _sqlite_to_model(values):
        """Convert a tuple of SQLite values to a PaymentChannelModel.

        Args:
            values (tuple): Tuple of SQLite values representing a PaymentChannelModel.

        Returns:
            PaymentChannelModel: Payment channel state model.

        """
        url = values[0]
        state = PaymentChannelState[values[1]]
        creation_time = values[2]
        deposit_tx = bitcoin.Transaction.from_hex(values[3]) if values[3] else None
        refund_tx = bitcoin.Transaction.from_hex(values[4]) if values[4] else None
        payment_tx = bitcoin.Transaction.from_hex(values[5]) if values[5] else None
        spend_tx = bitcoin.Transaction.from_hex(values[6]) if values[6] else None
        spend_txid = values[7]
        min_output_amount = values[8]

        return PaymentChannelModel(
            url=url,
            state=state,
            creation_time=creation_time,
            deposit_tx=deposit_tx,
            refund_tx=refund_tx,
            payment_tx=payment_tx,
            spend_tx=spend_tx,
            spend_txid=spend_txid,
            min_output_amount=min_output_amount,
        )

    def create(self, model):
        values = self._model_to_sqlite(model)
        self._conn.execute("INSERT INTO channels VALUES (?,?,?,?,?,?,?,?,?)", values)

    def read(self, url):
        cur = self._conn.execute("SELECT * FROM channels WHERE url=? LIMIT 1", (url,))
        return self._sqlite_to_model(cur.fetchone())

    def update(self, model):
        values = self._model_to_sqlite(model)
        self._conn.execute("UPDATE channels SET state=?, creation_time=?, deposit_tx=?, refund_tx=?, payment_tx=?, spend_tx=?, spend_txid=?, min_output_amount=? WHERE url=?", values[1:] + (values[0],))  # nopep8

    def list(self):
        cur = self._conn.execute("SELECT url FROM channels")
        return [row[0] for row in cur.fetchall()]

    @property
    def lock(self):
        return self._lock

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if not exc_type and not exc_value and not traceback:
            self._conn.commit()
        else:
            self._conn.rollback()


class Sqlite3DatabaseLock:
    """Sqlite3 multi-threading and multi-process database lock."""

    def __init__(self, db_path):
        self._db_fd = os.open(db_path, os.O_RDWR)
        self._thread_lock = threading.Lock()

    def __enter__(self):
        # Lock the database interface (multi-threading)
        self._thread_lock.acquire()

        # Lock the database (multi-processing)
        fcntl.lockf(self._db_fd, fcntl.LOCK_EX)

    def __exit__(self, exc_type, exc_value, traceback):
        # Unlock the database (multi-processing)
        fcntl.lockf(self._db_fd, fcntl.LOCK_UN)

        # Unlock the database interface (multi-threading)
        self._thread_lock.release()
