import math
from unittest.mock import MagicMock

from two1.bitcoin.crypto import HDKey, HDPrivateKey, HDPublicKey
from two1.bitcoin.txn import Transaction
from two1.wallet.bip44_account import BIP44Account
from two1.wallet.txn_data_provider import TransactionDataProvider

class MockTxnDict(dict):
    def __init__(self, num_used, addr_range, addr_list, used_value, unused_value):
        self.num_used = num_used
        self.addr_range = addr_range
        self.addr_list = addr_list
        self.used_value = used_value
        self.unused_value = unused_value

        self.start = max([0, self.addr_range.start])
        self.end = min([self.num_used, self.addr_range.stop])
        
    def __getitem__(self, item):
        if item in self:
            return self.used_value
        else:
            return self.unused_value

    def __contains__(self, item):
        if self.num_used == 0 or self.start > self.end:
            return False

        return item in self.addr_list[self.start:self.end]


class MockTransactionDataProvider(TransactionDataProvider):
    methods = ['get_balance', 'get_transactions', 'get_utxo',
               'get_balance_hd', 'get_transactions_hd', 'get_utxo_hd',
               'send_transaction']
    address_increment = 2 * BIP44Account.GAP_LIMIT
    max_address = 2 * address_increment
    
    def __init__(self, hd_acct_key, non_hd_addr_list=[]):
        super().__init__()

        self.addr_list = non_hd_addr_list
        self.hd_acct_key = hd_acct_key

        self._num_used_payout_addresses = 0
        self._num_used_change_addresses = 0

        for m in self.methods:
            setattr(self, m, MagicMock())

        self._setup_balances_hd()
        
    def reset_mocks(self, methods=[]):
        if not methods:
            methods = self.methods

        for m in methods:
            if hasattr(self, m):
                g = getattr(self, m)
                g.reset_mock()

    @property
    def hd_acct_key(self):
        return self._hd_acct_key

    @hd_acct_key.setter
    def hd_acct_key(self, k):
        self._hd_acct_key = k

        self.payout_key = HDPrivateKey.from_parent(self._hd_acct_key, 0)
        self.change_key = HDPrivateKey.from_parent(self._hd_acct_key, 1)
                
        self.payout_addresses = [HDPublicKey.from_parent(self.payout_key.public_key, i).address()
                                 for i in range(self.max_address)]
        self.change_addresses = [HDPublicKey.from_parent(self.change_key.public_key, i).address()
                                 for i in range(self.max_address)]

    @property
    def num_used_payout_addresses(self):
        return self._num_used_payout_addresses

    @num_used_payout_addresses.setter
    def num_used_payout_addresses(self, n):
        self._num_used_payout_addresses = n
        self._setup_balances_hd()

    @property
    def num_used_change_addresses(self):
        return self._num_used_change_addresses

    @num_used_change_addresses.setter
    def num_used_change_addresses(self, n):
        self._num_used_change_addresses = n
        self._setup_balances_hd()

    def _setup_balances_hd(self):
        d = {a: (0, 10000) for a in self.change_addresses[:self._num_used_change_addresses]}
        d.update({a: (100000, 0) for a in self.payout_addresses[:self._num_used_payout_addresses]})
        self.get_balance_hd = MagicMock(return_value=d)
        
    def set_txn_side_effect_for_hd_discovery(self, change, append=False):
        dummy_txn = Transaction(1, [], [], 0)
        effects = [e for e in self.get_transactions.side_effect] if append else []

        num_used = self._num_used_change_addresses if change else self._num_used_payout_addresses
        r = math.ceil(num_used / self.address_increment)
        addr_list = self.change_addresses if change else self.payout_addresses

        if r == 0:
            r = 1
        for i in range(r):
            effects.append(MockTxnDict(num_used=num_used,
                                       addr_range=range(i * self.address_increment, (i + 1) * self.address_increment),
                                       addr_list=addr_list,
                                       used_value=[dummy_txn],
                                       unused_value=[]))

        self.get_transactions.side_effect = effects
        
        return len(effects)

    
