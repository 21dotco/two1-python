import time
from two1.bitcoin.crypto import HDKey, HDPrivateKey, HDPublicKey
from two1.wallet.wallet_txn import WalletTransaction


class HDAccount(object):
    """ An implementation of a single HD account to be used in an HD
    wallet.

    This class handles key generation/management for both internal
    (change) and external (payout) purposes. If provided with only
    a public key, it is only useful for public key
    generation/management. If a private key is provided instead,
    private keys can be generated for signing (spending) purposes.

    Transaction signing capability is NOT provided by this class.
    This is a conscious design decision as the wallet is better
    suited to signing & spending as there may be situations
    requiring spending coins from multiple accounts in a single
    transaction.

    This relies on a data provider that derives from
    TransactionDataProvider, which provides transaction data and
    balance information for provided addresses.

    Args:
        hd_key (HDKey): Either a HDPrivateKey (enables private key
           generation) or HDPublicKey which is the root of this account.
        name (str): Name of this account
        index (int): Child index of this account relative to the parent.
        data_provider (BaseProvider): A compatible data provider.
        testnet (bool): Whether or not this account will be used on testnet.
    """
    PAYOUT_CHAIN = 0
    CHANGE_CHAIN = 1
    GAP_LIMIT = 20
    DISCOVERY_INCREMENT = 100
    MAX_UPDATE_THRESHOLD = 30  # seconds

    def __init__(self, hd_key, name, index, data_provider, cache_manager,
                 testnet=False, last_state=None, skip_discovery=False):
        # Take in either public or private key for this account as we
        # can derive everything from it.
        if not isinstance(hd_key, HDKey):
            raise TypeError("hd_key must be a HDKey object")

        self.key = hd_key
        self.name = name
        self.index = index
        self.data_provider = data_provider
        self.testnet = testnet

        self.last_indices = [-1, -1]
        self._cache_manager = cache_manager
        self._last_update = 0
        self._last_full_update = 0

        if last_state is not None and isinstance(last_state, dict):
            if "last_payout_index" in last_state:
                self.last_indices[self.PAYOUT_CHAIN] = last_state["last_payout_index"]
            if "last_change_index" in last_state:
                self.last_indices[self.CHANGE_CHAIN] = last_state["last_change_index"]

        # Check to see that the address cache has up to last_indices
        for change in [self.PAYOUT_CHAIN, self.CHANGE_CHAIN]:
            k = self._cache_manager.get_chain_indices(self.index, change)
            for i in range(self.last_indices[change] + 1):
                if i not in k or k[i] != i:
                    self.last_indices[change] = -1
                    break

        self._chain_priv_keys = [None, None]
        self._chain_pub_keys = [None, None]

        for change in [0, 1]:
            if isinstance(self.key, HDPrivateKey):
                self._chain_priv_keys[change] = HDPrivateKey.from_parent(self.key, change)
                self._chain_pub_keys[change] = self._chain_priv_keys[change].public_key
            else:
                self._chain_pub_keys[change] = HDPublicKey.from_parent(self.key, change)

        if not skip_discovery:
            self._sync_txns(check_all=True)
            self._update_balance()

    def _sync_txns(self, max_index=0, check_all=False):
        now = time.time()
        if now - self._last_full_update > 20 * 60:
            check_all = True

        for change in [0, 1]:
            found_last = False
            current_last = self.last_indices[change]

            addr_range = 0
            while not found_last:
                # Try a 2 * GAP_LIMIT at a go
                end = addr_range + self.DISCOVERY_INCREMENT
                addresses = {i: self.get_address(change, i)
                             for i in range(addr_range, end)}

                if self.data_provider.can_limit_by_height:
                    min_block = None if check_all else self._cache_manager.last_block
                    txns = self.data_provider.get_transactions(
                        list(addresses.values()),
                        limit=10000,
                        min_block=min_block)
                else:
                    txns = self.data_provider.get_transactions(
                        list(addresses.values()),
                        limit=10000)

                inserted_txns = set()
                for i in sorted(addresses.keys()):
                    addr = addresses[i]

                    self._cache_manager.insert_address(self.index, change, i, addr)

                    addr_has_txns = self._cache_manager.address_has_txns(addr)

                    if not addr_has_txns or addr not in txns or \
                       not bool(txns[addr]):
                        if i - current_last >= self.GAP_LIMIT:
                            found_last = True
                            break

                    if txns[addr]:
                        current_last = i
                        for t in txns[addr]:
                            txid = str(t['transaction'].hash)
                            if txid not in inserted_txns:
                                wt = WalletTransaction.from_transaction(
                                    t['transaction'])
                                wt.block = t['metadata']['block']
                                wt.block_hash = t['metadata']['block_hash']
                                wt.confirmations = t['metadata']['confirmations']
                                if 'network_time' in t['metadata']:
                                    wt.network_time = t['metadata']['network_time']
                                self._cache_manager.insert_txn(wt)
                                inserted_txns.add(txid)

                    if addr_has_txns:
                        current_last = i

                addr_range += self.DISCOVERY_INCREMENT

            self.last_indices[change] = current_last

        self._last_update = time.time()
        if check_all:
            self._last_full_update = self._last_update

    def _update_balance(self):
        balance = {'confirmed': 0, 'total': 0}
        self._address_balances = {}
        for unconfirmed in [True, False]:
            addr_balances = self._cache_manager.get_balances(
                addresses=self.all_used_addresses,
                include_unconfirmed=unconfirmed)

            key = 'total' if unconfirmed else 'confirmed'
            for k, v in addr_balances.items():
                if k not in self._address_balances:
                    self._address_balances[k] = {'confirmed': 0, 'total': 0}
                self._address_balances[k][key] = v
                balance[key] += v

        self._balance_cache = balance

    def has_txns(self):
        """ Returns whether or not there are any discovered transactions
        associated with any address in the account.

        Returns:
            bool: True if there are discovered transactions, False otherwise.
        """
        return self._cache_manager.has_txns(self.index)

    def find_addresses(self, addresses):
        """ Searches both the change and payout chains up to self.GAP_LIMIT
        addresses beyond the last known index for the chain.

        Args:
            addresses (list(str)): List of Base58Check encoded addresses

        Returns:
            dict:
                Dictionary keyed by address where the value is a tuple
                containing the chain (0 or 1) and child index in the chain.
                Only found addresses are included in the dict.
        """
        found = {}
        for change in [0, 1]:
            for i in range(self.last_indices[change] + self.GAP_LIMIT + 1):
                addr = self.get_address(change, i)

                if addr in addresses:
                    found[addr] = (self.index, change, i)

        return found

    def get_public_key(self, change, n=-1):
        """ Returns a public key in the chain

        Args:
            change (bool): If True, returns an address for change purposes,
               otherwise returns an address for payment.
            n (int): index of address in chain. If n == -1, a new key
               is created with index = self.last_[change|payout]_index + 1

        Returns:
            HDPublicKey: A public key in this account's chain.
        """
        # We only use public key derivation per BIP44
        c = int(change)
        k = self._chain_pub_keys[c]
        if n < 0:
            self.last_indices[c] += 1
            i = self.last_indices[c]
            pub_key = HDPublicKey.from_parent(k, i)
            addr = pub_key.address(True, self.testnet)
            self._cache_manager.insert_address(self.index, change, i, addr)
        else:
            pub_key = HDPublicKey.from_parent(k, n)

        return pub_key

    def get_private_key(self, change, n):
        """ Returns a private key in the chain for use in signing messages
        or transactions.

        Args:
            change (bool): If True, returns an address for change purposes,
               otherwise returns an address for payment.
            n (int): index of address in chain.

        Returns:
            HDPrivateKey: A private key in this account's chain.
        """
        # We only use public key derivation per BIP44
        k = self._chain_priv_keys[change]
        if k is None:
            raise ValueError("No private key provided for account.")
        return HDPrivateKey.from_parent(k, n)

    def get_address(self, change, n=-1):
        """ Returns a public address

        Args:
            change (bool): If True, returns an address for change purposes,
               otherwise returns an address for payment.
            n (int): index of address in chain. If n == -1, a new key
               is created with index = self.last_[change|payout]_index + 1

        Returns:
            str: A bitcoin address
        """
        # If this is an address we've already generated, don't regenerate.
        c = int(change)
        cached = self._cache_manager.get_address(self.index, c, n)
        if cached is not None:
            return cached

        # Always do compressed keys
        return self.get_public_key(change, n).address(True, self.testnet)

    def _new_key_or_address(self, change, key=False):
        c = int(change)
        last_index = self.last_indices[c]

        # Check to see if the current address has any txns
        # associated with it before giving out a new one.
        ret = None
        need_new = False
        if last_index >= 0:
            current_addr = self._cache_manager.get_address(self.index, c, last_index)
            need_new = self._cache_manager.address_has_txns(current_addr)
        else:
            need_new = True

        if need_new:
            ret = self.get_public_key(change) if key else self.get_address(change, last_index + 1)
        else:
            ret = self.get_public_key(change, last_index) if key else current_addr

        return ret

    def get_next_address(self, change):
        """ Returns the next public address in the specified chain.

        A new address is only returned if there are transactions found
        for the current address.

        Args:
            change (bool): If True, returns an address for change purposes,
               otherwise returns an address for payment.

        Returns:
            str: A bitcoin address
        """
        return self._new_key_or_address(change)

    def get_next_public_key(self, change):
        """ Returns the next public key in the specified chain.

        A new key is only returned if there are transactions found
        for the current key.

        Args:
            change (bool): If True, returns a PublicKey for change purposes,
               otherwise returns a PublicKey for payment.

        Returns:
            PublicKey: A public key
        """
        return self._new_key_or_address(change, True)

    def get_utxos(self, include_unconfirmed=False):
        """ Gets all unspent transactions associated with all addresses
            up to and including the last known indices for both change
            and payout chains.
        """
        return self._cache_manager.get_utxos(addresses=self.all_used_addresses,
                                             include_unconfirmed=include_unconfirmed)

    def to_dict(self):
        """ Returns a JSON-serializable dict to save account data

        Returns:
            dict: Dict that can be serialized into a JSON string
        """
        if isinstance(self.key, HDPublicKey):
            pub_key = self.key
        else:
            pub_key = self.key.public_key
        return {"public_key": pub_key.to_b58check(self.testnet),
                "last_payout_index": self.last_indices[self.PAYOUT_CHAIN],
                "last_change_index": self.last_indices[self.CHANGE_CHAIN]}

    def balances_by_address(self):
        """ Returns a dict with balances for each used
        address in the account

        Returns:
            dict: key/values are addresses and current balance
        """
        return self._address_balances

    @property
    def balance(self):
        """ Returns balances, both confirmed and total, for this
        account.

        Returns:
            dict:
                'confirmed' and 'total' keys with balance values in
                satoshis for each. The total balance includes
                unconfirmed transactions.
        """
        self._update_balance()
        return self._balance_cache

    @property
    def all_used_addresses(self):
        """ List of all used addresses

        Returns:
            list(str): list of all used addresses (Base58Check encoded)
        """
        all_addresses = []
        for change in [self.PAYOUT_CHAIN, self.CHANGE_CHAIN]:
            last = self.last_indices[change]
            all_addresses += [self.get_address(change, i)
                              for i in range(last + 1)]

        return all_addresses
