"""This submodule provides a concrete `MockProvider` class that provides
information about a blockchain by contacting a server."""
import math
from unittest.mock import MagicMock

from two1.bitcoin.crypto import HDKey, HDPrivateKey, HDPublicKey
from two1.bitcoin.hash import Hash
from two1.bitcoin.script import Script
from two1.bitcoin.txn import TransactionOutput
from two1.bitcoin.txn import Transaction
from two1.bitcoin.utils import address_to_key_hash
from two1.blockchain.base_provider import BaseProvider
from two1.wallet.account_types import AccountType
from two1.wallet.account_types import account_types
from two1.wallet.hd_account import HDAccount


class MockTxnDict(dict):
    def __init__(self, num_used, addr_range,
                 addr_list, used_value, unused_value):
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


class MockProvider(BaseProvider):
    methods = ['get_balance', 'get_transactions', 'get_utxos',
               'send_transaction']
    address_increment = HDAccount.DISCOVERY_INCREMENT
    max_address = 8 * address_increment
    max_accounts = 10

    def __init__(self, hd_account_type, hd_master_key, non_hd_addr_list=[]):
        super().__init__()

        if isinstance(hd_account_type, str):
            if hd_account_type not in account_types:
                raise ValueError("hd_account_type must be one of %r." %
                                 account_types.keys())
            else:
                self.account_type = account_types[hd_account_type]
        elif isinstance(hd_account_type, AccountType):
            self.account_type = hd_account_type
        else:
            raise TypeError("hd_account_type should be a str or AccountType object")

        self._num_used_addresses = {}
        self._num_used_accounts = 0

        for i in range(self.max_accounts):
            self._num_used_addresses[i] = {0: 0, 1: 0}

        self.addr_list = non_hd_addr_list
        self.hd_master_key = hd_master_key

        for m in self.methods:
            setattr(self, m, MagicMock())

        self._setup_balances()

    def reset_mocks(self, methods=[]):
        if not methods:
            methods = self.methods

        for m in methods:
            if hasattr(self, m):
                g = getattr(self, m)
                g.reset_mock()

    @property
    def hd_master_key(self):
        return self._hd_master_key

    @hd_master_key.setter
    def hd_master_key(self, k):
        self._hd_master_key = k
        self._acct_keys = {}

        keys = HDKey.from_path(self._hd_master_key,
                               self.account_type.account_derivation_prefix)
        for i in range(self.max_accounts):
            acct_key = HDPrivateKey.from_parent(keys[-1], 0x80000000 | i)
            payout_key = HDPrivateKey.from_parent(acct_key, 0)
            change_key = HDPrivateKey.from_parent(acct_key, 1)

            payout_addresses = [HDPublicKey.from_parent(payout_key.public_key, i).address()
                                for i in range(self.max_address)]
            change_addresses = [HDPublicKey.from_parent(change_key.public_key, i).address()
                                for i in range(self.max_address)]

            self._acct_keys[i] = {'acct_key': acct_key,
                                  'payout_key': payout_key,
                                  'change_key': change_key,
                                  'payout_addresses': payout_addresses,
                                  'change_addresses': change_addresses}

            self._num_used_addresses[i][0] = 0
            self._num_used_addresses[i][1] = 0

        self._setup_balances()

    def set_num_used_addresses(self, account_index, n, change):
        self._num_used_addresses[account_index][change] = n
        self._setup_balances()

    def set_num_used_accounts(self, n):
        self._num_used_accounts = n
        self._setup_balances()

    def _setup_balances(self):
        d = {}
        for i in range(self._num_used_accounts):
            payout_addresses = self._acct_keys[i]['payout_addresses'][:self._num_used_addresses[i][0]]
            change_addresses = self._acct_keys[i]['change_addresses'][:self._num_used_addresses[i][1]]

            cd = {'confirmed': 0, 'total': 10000}
            pd = {'confirmed': 100000, 'total': 100000}
            d.update({a: cd for a in change_addresses})
            d.update({a: pd for a in payout_addresses})

        self.get_balance = MagicMock(return_value=d)

    def set_txn_side_effect_for_index(self, account_index, address_index,
                                      change):
        dummy_txn = Transaction(1, [], [], 0)
        metadata = dict(block_height=234790,
                        block_hash=Hash("000000000000000007d57f03ebe36dbe4f87ab2f340e93b45999ab249b6dc0df"),
                        confirmations=23890)

        k = 'change_addresses' if change else 'payout_addresses'
        addr_list = self._acct_keys[account_index][k]
        mtd = MockTxnDict(num_used=address_index + 1,
                          addr_range=range(address_index, address_index + 1),
                          addr_list=addr_list,
                          used_value=[dict(metadata=metadata,
                                           transaction=dummy_txn)],
                          unused_value=[])
        self.get_transactions.side_effect = [mtd]

    def set_txn_side_effect_for_hd_discovery(self):
        # For each used account, there are at least 2 calls required:
        # 1 for the first DISCOVERY_INCREMENT payout addresses and 1
        # for the first DISCOVERY_INCREMENT change
        # addresses. Depending on the number of used addresses for the
        # account, this will change.

        effects = []

        n = self._num_used_accounts
        if n == 0:
            n = 1

        for acct_num in range(n):
            for change in [0, 1]:
                num_used = self._num_used_addresses[acct_num][change]
                r = math.ceil((num_used + HDAccount.GAP_LIMIT) /
                              self.address_increment)
                k = 'change_addresses' if change else 'payout_addresses'
                addr_list = self._acct_keys[acct_num][k]

                if change:
                    metadata = dict(block=234790 + r,
                                    block_hash=Hash("000000000000000007d57f03ebe36dbe4f87ab2f340e93b45999ab249b6dc0df"),
                                    confirmations=23890 - r)
                else:
                    metadata = dict(block=None,
                                    block_hash=None,
                                    confirmations=0)

                if r == 0:
                    r = 1
                for i in range(r):
                    start = i * self.address_increment
                    end = (i + 1) * self.address_increment
                    addr_range = range(start, end)

                    out = TransactionOutput(value=10000,
                                            script=Script.build_p2pkh(
                                                address_to_key_hash(
                                                    addr_list[i])[1]))
                    dummy_txn = Transaction(1,
                                            [],
                                            [out],
                                            0)

                    m = MockTxnDict(num_used=num_used,
                                    addr_range=addr_range,
                                    addr_list=addr_list,
                                    used_value=[dict(metadata=metadata,
                                                     transaction=dummy_txn)],
                                    unused_value=[])
                    effects.append(m)

        self.get_transactions.side_effect = effects

        return len(effects)
