import copy

from two1.bitcoin.hash import Hash
from two1.bitcoin.txn import Transaction


class WalletTransaction(Transaction):
    """
    """

    @staticmethod
    def from_bytes(b):
        """ Deserializes a byte stream into a WalletTransaction.

        Args:
            b (bytes): byte stream starting with the version.

        Returns:
            tuple: First element of the tuple is the WalletTransaction,
                   second is the remainder of the byte stream.
        """
        t, b1 = Transaction.from_bytes()
        return WalletTransaction.from_transaction(t), b1

    @staticmethod
    def from_hex(h):
        return WalletTransaction.from_transaction(
            Transaction.from_hex(h))

    @staticmethod
    def from_transaction(txn):
        """ Creates a wallet transaction object from a normal bitcoin
            library transaction.

        Args:
            txn (Transaction): The bitcoin transaction object to
                create this from.

        Returns:
            WalletTransaction: A WalletTransaction object
        """
        txn_copy = copy.deepcopy(txn)
        rv = WalletTransaction(version=txn_copy.version,
                               inputs=txn_copy.inputs,
                               outputs=txn_copy.outputs,
                               lock_time=txn_copy.lock_time)

        return rv

    @staticmethod
    def _deserialize(wt_dict):
        # Private, only for internal wallet usage
        wt = WalletTransaction.from_hex(wt_dict['transaction'])
        if 'metadata' in wt_dict:
            m = wt_dict['metadata']
        else:
            m = wt_dict
        wt.block = m['block']
        if m['block_hash'] is not None:
            wt.block_hash = Hash(m['block_hash'])
        wt.confirmations = m['confirmations']
        wt.network_time = m['network_time']
        if 'value' in m:
            wt.value = m['value']
        if 'fees' in m:
            wt.fees = m['fees']
        if 'provisional' in m:
            wt.provisional = m['provisional']

        return wt

    def __init__(self, version, inputs, outputs, lock_time,
                 block=None, block_hash=None, confirmations=0,
                 network_time=0, value=0, fees=0):
        super().__init__(version, inputs, outputs, lock_time)

        self.block = block
        self.block_hash = block_hash
        self.confirmations = confirmations
        self.network_time = network_time
        self.value = value
        self.fees = fees
        self.provisional = False

    def __eq__(self, o):
        return self._serialize() == o._serialize()

    def _serialize(self):
        # Private, only for internal wallet usage
        h = None if self.block_hash is None else str(self.block_hash)
        return dict(transaction=self.to_hex(),
                    block=self.block,
                    block_hash=h,
                    confirmations=self.confirmations,
                    network_time=self.network_time,
                    value=self.value,
                    fees=self.fees,
                    provisional=self.provisional)
