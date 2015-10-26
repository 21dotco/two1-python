import sqlite3


class OnChainError(Exception):
    pass


class ModelNotFound(OnChainError):
    pass


class OnChainDatabase:

    def __init__(self):
        pass

    def create(txid):
        pass

    def lookup(txid):
        pass

##############################################################################


class OnChainSQLite3(OnChainDatabase):

    def __init__(self):
        """Instantiate SQLite3 for storing on chain transaction data."""
        self.connection = sqlite3.connect('payment.sqlite3', check_same_thread=False)
        self.c = self.connection.cursor()
        self.c.execute("CREATE TABLE IF NOT EXISTS 'payment_onchain' (txid text, amount integer)")

    def _return_dict(self, txid, amount):
        """Format return data."""
        return {'txid': txid, 'amount': amount}

    def create(self, txid, amount):
        """Create a transaction entry."""
        insert = 'INSERT INTO payment_onchain VALUES (?, ?)'
        self.c.execute(insert, (txid, amount))
        self.connection.commit()
        return self._return_dict(txid, amount)

    def lookup(self, txid):
        """Look up a transaction entry."""
        select = 'SELECT txid, amount FROM payment_onchain WHERE txid=?'
        self.c.execute(select, (txid,))
        rv = self.c.fetchone()
        if rv is None:
            raise ModelNotFound()
        return self._return_dict(rv[0], rv[1])

    def get_or_create(self, txid, amount):
        """Attempt a lookup and create the record if it doesn't exist."""
        try:
            return self.lookup(txid), False
        except ModelNotFound as e:
            return self.create(txid, amount), True
