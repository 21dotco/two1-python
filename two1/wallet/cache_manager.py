import json
import os
import time

from two1.bitcoin.hash import Hash
from two1.bitcoin.script import Script
from two1.bitcoin.txn import CoinbaseInput
from two1.bitcoin.txn import TransactionInput
from two1.bitcoin.txn import TransactionOutput
from two1.bitcoin.txn import Transaction
from two1.bitcoin.txn import UnspentTransactionOutput
from two1.bitcoin.utils import key_hash_to_address
from two1.wallet.wallet_txn import WalletTransaction


class CacheManager(object):
    """ This is a glorified dict that provides relational methods
        for getting transactions for addresses, etc.
    """
    # Statuses
    UNCONFIRMED = 0x10
    PROVISIONAL = 0x20
    SPENT = 0x1
    UNSPENT = 0x2
    UNKNOWN = 0x3

    PROVISIONAL_MAX_DURATION = 60*60  # 60 minutes
    CACHE_VERSION = "0.3.0"

    def __init__(self, testnet=False):
        self._address_cache = {}
        self._txns_by_addr = {}
        self._deposits_for_addr = {}
        self._spends_for_addr = {}
        self._inputs_cache = {}
        self._outputs_cache = {}
        self._txn_cache = {}

        self._dirty = False

        self._last_block = None

        self.testnet = testnet

    @property
    def last_block(self):
        """ Returns the last block the cache knows about

        Returns:
            int: The block height of the last known block.
        """
        return self._last_block

    @last_block.setter
    def last_block(self, b):
        if self._last_block is None or b > self._last_block:
            self._last_block = b
            self._dirty = True

    def _serialize_cache(self, cache):
        """ Serializes a cache into a dict capable of being used
            as an arg to json.dumps().
        """
        newd = {}
        for k, v in cache.items():
            if isinstance(v, dict):
                newd[k] = self._serialize_cache(v)
            elif isinstance(v, WalletTransaction):
                newd[k] = v._serialize()
            elif isinstance(v, Transaction):
                newd[k] = WalletTransaction.from_transaction(v)._serialize()
            elif isinstance(v, TransactionInput) or isinstance(v, TransactionOutput):
                newd[k] = str(v)
            elif isinstance(v, Hash):
                newd[k] = str(v)
            elif isinstance(v, set):
                newd[k] = list(v)
            else:
                newd[k] = v

        return newd

    def to_file(self, filename, force=False):
        """ Serializes the cache data to a file such that it is
            recoverable using `from_file`. If the caches are not dirty,
            by default, nothing will be written. However, this can be
            modified by setting force=True.

        Args:
            filename (str): The full path of the file to write the
                caches to. If the file exists, it will be overwritten.
            force (bool): Forces a write to the file even if the caches
                are clean.
        """
        if not self._dirty and not force:
            return

        # All we really need to serialize is the address and txn caches
        d = json.dumps(dict(addresses=self._address_cache,
                            txns=self._serialize_cache(self._txn_cache),
                            last_block=self.last_block,
                            version=self.CACHE_VERSION),
                       sort_keys=True).encode('utf-8')

        p = os.path.abspath(filename)

        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        with os.fdopen(os.open(p, flags=flags, mode=0o700), 'wb') as fp:
            fp.write(d)

        self._dirty = False

    def load_from_dict(self, d, prune_provisional=True):
        """ Loads the cache manager from a dict

        Args:
            d (dict): A dict of the type created by to_file.
            prune_provisional (bool): If True, does not insert
                provisionally-marked txns that are older than
                self.PROVISIONAL_TXN_TIMEOUT.
        """
        if "version" not in d or d["version"] != self.CACHE_VERSION:
            return

        if "last_block" in d:
            self.last_block = d['last_block']

        if "addresses" in d:
            # Make the keys integers
            self._address_cache = {int(k1): {int(k2): {int(k3): v3
                                                       for k3, v3 in v2.items()}
                                             for k2, v2 in v1.items()}
                                   for k1, v1 in d['addresses'].items()}

        if "txns" in d:
            now = time.time()
            for txid in d['txns']:
                t = WalletTransaction._deserialize(d['txns'][txid])
                if t.provisional:
                    if not prune_provisional or \
                       t.provisional > now:
                        self.insert_txn(t,
                                        mark_provisional=True,
                                        expiration=t.provisional)
                else:
                    self.insert_txn(t, mark_provisional=False)

        self._dirty = True

    def load_from_file(self, filename):
        """ Loads the dicts from a JSON-serialized file.

        Args:
            filename (str): The full path of the file containing the
                JSON-serialized dicts.
        """
        cache_file = os.path.abspath(filename)
        with open(cache_file) as cf:
            cache = json.load(cf)

        self.load_from_dict(cache)

    def insert_address(self, acct_index, chain, index, address):
        """ Inserts an address into the cache

        Args:
            acct_index (int): Account index within wallet
            chain (int): Either HDAccount.CHANGE_CHAIN or
                HDAccount.PAYOUT_CHAIN
            index (int): The index in the chain
            address (str): The address to insert
        """
        if chain not in [0, 1]:
            raise ValueError("chain must be either 0 or 1")

        curr = self.get_address(acct_index, chain, index)
        if curr is not None:
            return

        if acct_index not in self._address_cache:
            self._address_cache[acct_index] = {0: {}, 1: {}}

        self._address_cache[acct_index][chain][index] = address

        self._dirty = True

    def get_address(self, acct_index, chain, index):
        """ Returns the address for chain/index, if it exists in the cache

        Args:
            acct_index (int): Account index within wallet
            chain (int): Either HDAccount.CHANGE_CHAIN or
                HDAccount.PAYOUT_CHAIN
            index (int): The index in the chain

        Returns:
            str or None: The address, or None if it's not in the cache
        """
        if chain not in [0, 1]:
            raise ValueError("chain must be either 0 or 1")

        rv = None
        if acct_index in self._address_cache and \
           chain in self._address_cache[acct_index]:
            rv = self._address_cache[acct_index][chain].get(index, None)

        return rv

    def get_addresses_for_chain(self, acct_index, chain):
        """ Returns all addresses for a particular chain, in order by
            their index in the chain.

        Args:
            acct_index (int): Account index within wallet
            chain (int): Either HDAccount.CHANGE_CHAIN or
                HDAccount.PAYOUT_CHAIN

        Returns:
            list: List of addresses
        """
        if chain not in [0, 1]:
            raise ValueError("chain must be either 0 or 1")

        rv = []
        if acct_index in self._address_cache:
            rv = [x[1] for x in
                  sorted(self._address_cache[acct_index][chain].items(),
                         key=lambda x: x[0])]

        return rv

    def get_chain_indices(self, acct_index, chain):
        """ Returns the address indices that are present in the cache
            for the desired chain.

        Args:
            acct_index (int): Account index within wallet
            chain (int): Either HDAccount.CHANGE_CHAIN or
                HDAccount.PAYOUT_CHAIN

        Returns:
            list: List of addresses
        """
        if chain not in [0, 1]:
            raise ValueError("chain must be either 0 or 1")

        rv = []
        if acct_index in self._address_cache:
            rv = sorted(list(self._address_cache[acct_index][chain].keys()))

        return rv

    def insert_txn(self, wallet_txn, mark_provisional=False, expiration=0):
        """ Inserts a transaction into the cache and updates the
            relevant dicts based on the addresses found in the
            transaction.

        Args:
            wallet_txn (WalletTransaction): A wallet transaction object.
            mark_provisional (bool): Marks the transaction as
                provisional (i.e. the transaction may have been built
                but not yet broadcast to the blockchain). Transactions
                marked as provisional are automatically pruned if they
                are not also seen by normal transaction
                updates/insertions within a certain time period.
            expiration (int): Time, in seconds from epoch, when a provisional
                transaction should be automatically pruned. This is invalid
                unless mark_provisional=True. If expiration == 0, it is set
                to time.time() + PROVISIONAL_MAX_DURATION. This cannot be
                greater than PROVISIONAL_MAX_DURATION seconds in the future.
        """
        txid = str(wallet_txn.hash)

        # Check if it's already in with no change in status
        if txid in self._txn_cache and \
           wallet_txn._serialize() == self._txn_cache[txid]._serialize():
            return

        if mark_provisional and not wallet_txn.provisional:
            now = time.time()
            if expiration < 0:
                raise ValueError("expiration cannot be negative.")

            if expiration == 0 or \
               expiration > now + self.PROVISIONAL_MAX_DURATION:
                expiration = now + self.PROVISIONAL_MAX_DURATION
            wallet_txn.provisional = expiration

        if not mark_provisional and wallet_txn.provisional:
            wallet_txn.provisional = False

        self._txn_cache[txid] = wallet_txn

        conf = wallet_txn.confirmations > 0
        status = self.SPENT
        out_status = self.UNSPENT
        if not conf:
            status |= self.UNCONFIRMED
            out_status |= self.UNCONFIRMED
        if mark_provisional:
            status |= self.PROVISIONAL
            out_status |= self.PROVISIONAL

        # Get all the addresses for the transaction
        addrs = wallet_txn.get_addresses(self.testnet)

        if txid not in self._inputs_cache:
            self._inputs_cache[txid] = dict()

        if txid not in self._outputs_cache:
            self._outputs_cache[txid] = dict()

        for i, inp in enumerate(wallet_txn.inputs):
            self._inputs_cache[txid][i] = inp

            if not isinstance(inp, CoinbaseInput) and inp.script.is_multisig_sig():
                # Only keep the P2SH address
                sig_info = inp.script.extract_multisig_sig_info()
                redeem_version = Script.P2SH_TESTNET_VERSION if self.testnet \
                    else Script.P2SH_MAINNET_VERSION
                a = key_hash_to_address(
                    sig_info['redeem_script'].hash160(), redeem_version)

                addrs['inputs'][i] = [a]

            # Update the status of any outputs
            out_txid = str(inp.outpoint)
            if out_txid not in self._outputs_cache:
                self._outputs_cache[out_txid] = {}

            if inp.outpoint_index not in self._outputs_cache[out_txid]:
                d = dict(output=None,
                         status=status,
                         spend_txid=txid,
                         spend_index=i)
                self._outputs_cache[out_txid][inp.outpoint_index] = d
            else:
                x = self._outputs_cache[out_txid][inp.outpoint_index]
                x['status'] = status
                x['spend_txid'] = txid
                x['spend_index'] = i

        for i, out in enumerate(wallet_txn.outputs):
            if i in self._outputs_cache[txid]:
                o = self._outputs_cache[txid][i]
                o['output'] = out
                # Only update the status if it is unconfirmed unspent going
                # to confirmed unspent as it is possible that an input has
                # already marked it as spent.
                if not (o['status'] & self.SPENT):
                    o['status'] = out_status
            else:
                self._outputs_cache[txid][i] = dict(output=out,
                                                    status=out_status,
                                                    spend_txid=None,
                                                    spend_index=None)

        self._insert_txid(txid, addrs['inputs'], 'input')
        self._insert_txid(txid, addrs['outputs'], 'output')

        self._dirty = True

    def _insert_txid(self, txid, addresses, inout):
        """ Inserts a txid into either the spends or deposits cache.

        Note:
            THIS IS NOT A PUBLIC API.

        Args:
            txid (Hash): The txid to associate with the addresses.
            addresses (list): List of addresses associated with the input.
            inout (str): "input" if the txid is an input to the list of addresses,
                "output" if the txid is an output.
        """
        if inout == "input":
            cache = self._spends_for_addr
        elif inout == "output":
            cache = self._deposits_for_addr
        else:
            raise TypeError("inout must either be 'input' or 'output'")

        _txid = str(txid) if isinstance(txid, Hash) else txid

        for i, addrs in enumerate(addresses):
            for a in addrs:
                if a not in cache:
                    cache[a] = {}
                if txid not in cache[a]:
                    cache[a][_txid] = set()

                cache[a][_txid].add(i)

                if a not in self._txns_by_addr:
                    self._txns_by_addr[a] = set()
                self._txns_by_addr[a].add(_txid)

    def _delete_txn(self, txid):
        """ Removes a transaction from the cache and updates any
            ancestor/descendant transactions' statuses so that it was
            like this transaction didn't exist.

        Note:
            THIS IS NOT A PUBLIC API. Use prune_provisional_txns() to
            remove any transactions marked as provisional that may
            have "expired".

        Args:
            txid (Hash or str): The ID of the transaction to remove.
        """
        _txid = str(txid)
        if _txid not in self._txn_cache:
            return

        # Go through the inputs and outputs and update the statuses
        txn = self._txn_cache[_txid]
        addrs = txn.get_addresses(self.testnet)

        for i, inp in enumerate(txn.inputs):
            # Update the status of any outpoints
            out_txid = str(inp.outpoint)

            x = self._outputs_cache[out_txid][inp.outpoint_index]
            x['status'] = self.UNSPENT
            out_txn = self._txn_cache[out_txid]
            if out_txn.provisional:
                x['status'] |= self.PROVISIONAL
            if out_txn.confirmations == 0:
                x['status'] |= self.UNCONFIRMED
            x['spend_txid'] = None
            x['spend_index'] = None

        addresses = set()
        for addr_list in addrs['inputs'] + addrs['outputs']:
            for a in addr_list:
                addresses.add(a)

        for a in addresses:
            if a in self._txns_by_addr:
                if _txid in self._txns_by_addr[a]:
                    self._txns_by_addr[a].remove(_txid)

            for cache in [self._spends_for_addr, self._deposits_for_addr]:
                if a in cache and _txid in cache[a]:
                    del cache[a][_txid]
                    if not cache[a]:
                        del cache[a]

        if _txid in self._inputs_cache:
            del self._inputs_cache[_txid]

        if _txid in self._outputs_cache:
            del self._outputs_cache[_txid]

        del self._txn_cache[_txid]

        self._dirty = True

    def prune_provisional_txns(self):
        """ Removes transactions marked as provisional if they are past
            their expiration time.
        """
        now = time.time()
        txids = list(self._txn_cache.keys())
        for txid in txids:
            txn = self._txn_cache[txid]
            if txn.provisional and txn.provisional < now:
                self._delete_txn(txid)

    def has_txns(self, account_index=None):
        """ Returns whether or not there are any transactions in the cache.

        Args:
            account_index (int): The account to check. If None, returns
                whether there are any transactions in the cache.

        Returns:
            bool: True if there are any transactions, False otherwise.
        """
        if account_index is None:
            return bool(self._txn_cache)
        elif account_index in self._address_cache:
            for chain, chain_addrs in self._address_cache[account_index].items():
                for i, addr in chain_addrs.items():
                    if self.address_has_txns(addr):
                        return True

        return False

    def get_transaction(self, txid):
        """ Returns the transaction object and metadata for txid

        Args:
            txid (Hash): The txid to retrieve.

        Returns:
            dict: A dict containing 'metadata' and 'transaction' keys or
                None if the transaction is not in the cache.
        """
        _txid = str(txid) if isinstance(txid, Hash) else txid
        return self._txn_cache.get(_txid, None)

    def have_transaction(self, txid):
        """ Returns whether or not a txid (and associated transaction)
            is in the cache.

        Args:
            txid (Hash): The txid to retrieve.

        Returns:
            dict: A dict containing 'metadata' and 'transaction' keys or
                None if the transaction is not in the cache.
        """
        _txid = str(txid) if isinstance(txid, Hash) else txid
        return _txid in self._txn_cache and self._txn_cache[_txid]

    def get_txns_for_address(self, address):
        """ Returns a list of transactions for the address

        Args:
            address (str): The address to retrieve transactions for.

        Returns:
            list: A list of dicts containing transaction metadata and
               the Transaction object.
        """
        return list(self._txns_by_addr.get(address, set()))

    def address_has_txns(self, address):
        """ Returns whether or not an address has any transactions
            associated with it.

        Args:
            address (str): The address to check.

        Returns:
            bool: True if there are transactions for the address,
                False otherwise.
        """
        return bool(self.get_txns_for_address(address))

    def get_utxos(self, addresses, include_unconfirmed=False):
        """ Returns a dict containing the UTXOs for the desired
            addresses

        Args:
            addresses (list): List of addresses to get balances for
            include_unconfirmed (bool): True if unconfirmed
                transactions should be included in the balance.

        Returns:
            dict: Keys are addresses, values are lists of
                UnspentTransactionOutput objects for the address.
        """
        unconfirmed_mask = self.UNSPENT | self.UNCONFIRMED | self.PROVISIONAL
        rv = {}
        for addr in addresses:
            # Get the list of unspent deposits.
            if addr not in self._deposits_for_addr:
                continue

            for txid in self._deposits_for_addr[addr]:
                for i in self._deposits_for_addr[addr][txid]:
                    # Look up the status in the outputs cache
                    if txid not in self._outputs_cache or \
                       i not in self._outputs_cache[txid]:
                        raise Exception("Don't have information for %r:%r" %
                                        (txid, i))

                    status = self._outputs_cache[txid][i]['status']
                    if status & self.UNSPENT:
                        if (status & unconfirmed_mask and include_unconfirmed) or \
                           (status == self.UNSPENT and not include_unconfirmed):
                            out = self._outputs_cache[txid][i]['output']
                            utxo = UnspentTransactionOutput(
                                transaction_hash=Hash(txid),
                                outpoint_index=i,
                                value=out.value,
                                scr=out.script,
                                confirmations=self._txn_cache[txid].confirmations)

                            if addr not in rv:
                                rv[addr] = []
                            rv[addr].append(utxo)

        return rv

    def get_balances(self, addresses, include_unconfirmed=False):
        """ Returns a dict containing the balances for the desired
            addresses

        Args:
            addresses (list): List of addresses to get balances for
            include_unconfirmed (bool): True if unconfirmed
                transactions should be included in the balance.

        Returns:
            dict: Keys are addresses, values are balances for the address.
        """
        # Confirmed Balance = sum(all confirmed utxos) + unconfirmed spends
        utxos_by_addr = self.get_utxos(addresses, include_unconfirmed)

        balances = {}

        for addr, utxo_list in utxos_by_addr.items():
            balances[addr] = sum([u.value for u in utxo_list])

        for addr in addresses:
            if addr in self._spends_for_addr and not include_unconfirmed:
                # If we're doing confirmed balances, we need to add in
                # unconfirmed spends so that we're not unnecessarily
                # showing a lower confirmed balance
                for txid, indices in self._spends_for_addr[addr].items():
                    for i in indices:
                        inp = self._inputs_cache[txid][i]
                        out_txid = str(inp.outpoint)
                        out_index = inp.outpoint_index

                        # Don't add in chained unconfirmed spends
                        if self._txn_cache[out_txid].confirmations == 0:
                            continue

                        # Look up the outpoint index and see what
                        # the status is
                        out = self._outputs_cache[out_txid][out_index]
                        if (out['status'] & self.SPENT) and \
                           (out['status'] & self.UNCONFIRMED or out['status'] & self.PROVISIONAL):
                            if addr not in balances:
                                balances[addr] = 0
                            balances[addr] += out['output'].value

            # For any addresses that don't have UTXOs, set their
            # balance to 0
            if addr not in balances:
                balances[addr] = 0

        return balances
