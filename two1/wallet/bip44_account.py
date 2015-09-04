from two1.bitcoin.crypto import HDKey, HDPrivateKey, HDPublicKey

class BIP44Account(object):
    """ An implemenation of a single BIP44 account to be used in an HD
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
        index (int): child index of this account relative to the parent.
        txn_provider (TransactionDataProvider): A compatible data provider.
        testnet (bool): Whether or not this account will be used on testnet.
    """
    REQUIRED_DEPTH = 3
    PAYOUT_CHAIN = 0
    CHANGE_CHAIN = 1
    GAP_LIMIT = 20

    def __init__(self, hd_key, name, index, txn_provider, testnet=False):
        # Take in either public or private key for this account as we can derive
        # everything from it.
        # It must be depth = 3 following BIP44
        if not isinstance(hd_key, HDKey):
            raise TypeError("hd_key must be a HDKey object")

        assert hd_key.depth == self.REQUIRED_DEPTH
        
        self.key = hd_key
        self.name = name
        self.index = index
        self.txn_provider = txn_provider
        self.testnet = testnet

        self._chain_priv_keys = [None, None]
        self._chain_pub_keys = [None, None]
        self.last_indices = [None, None]
        for change in [0, 1]:
            if isinstance(self.key, HDPrivateKey):
                self._chain_priv_keys[change] = HDPrivateKey.from_parent(self.key, change)

            self._chain_pub_keys[change] = HDPublicKey.from_parent(self.key, change)

        self._discover_used_addresses()

    def _discover_used_addresses(self, max_index=0):
        self._txns = {}
        self._used_addresses = { self.CHANGE_CHAIN: [], self.PAYOUT_CHAIN: [] }
        
        for change in [0, 1]:
            found_last = False
            current_last = -1
            addr_range = 0
            all_addresses = []
            while not found_last:
                # Try a 2 * GAP_LIMIT at a go
                addresses = [self.get_address(change, i) for i in range(addr_range, addr_range + 2 * self.GAP_LIMIT)]
                all_addresses += addresses
                txns = self.txn_provider.get_transactions(addresses, 10000)

                for i, addr in enumerate(addresses):
                    global_index = addr_range + i
                    if addr not in txns or not bool(txns[addr]):
                        if global_index - current_last >= self.GAP_LIMIT:
                            found_last = True
                            break                        

                    if bool(txns[addr]):
                        # Do we want to cache transactions?
                        self._txns[addr] = txns[addr]
                        current_last = global_index

                addr_range += 2 * self.GAP_LIMIT

            self._used_addresses[change] = all_addresses[:current_last+1] if current_last != -1 else []
            self.last_indices[change] = current_last
                
    def has_txns(self):
        """ Returns whether or not there are any discovered transactions
            associated with any address in the account.

        Returns:
            bool: True if there are discovered transactions, False otherwise.
        """
        return bool(self._txns)

    def find_addresses(self, addresses):
        """ Searches both the change and payout chains up to self.GAP_LIMIT
            addresses beyond the last known index for the chain.

        Args:
            addresses (list(str)): List of Base58Check encoded addresses
        
        Returns:
            dict: Dictionary keyed by address where the value is a tuple
               containing the chain (0 or 1) and child index in the chain.
               Only found addresses are included in the dict.
        """
        found = {}
        for change in [0, 1]:
            for i in range(self.last_indices[change] + self.GAP_LIMIT + 1):
                # Save the key generation step for indices we already know about.
                addr = self._used_addresses[change][i] if i <= self.last_indices[change] else self.get_address(change, i)
                    
                if addr in addresses:
                    found[addr] = (self.index, change, i)

        return found
            
    def get_public_key(self, change, n=-1):
        """ Returns a public key in the chain

        Args:
            change (bool): If True, returns an address for change purposes,
               otherwise returns an address for payment.
            n (int): index of address in chain. If n == -1, a new key is created
               with index = self.last_[change|payout]_index + 1
        
        Returns:
            HDPublicKey: a public key in this account's chain.
        """
        # We only use public key derivation per BIP44
        k = self._chain_pub_keys[change]
        if n < 0:
            self.last_indices[int(change)] += 1
            pub_key = HDPublicKey.from_parent(k, self.last_indices[int(change)])
            self._used_addresses[int(change)].append(pub_key.address(True, self.testnet))
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
            HDPrivateKey: a private key in this account's chain.
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
            n (int): index of address in chain. If n == -1, a new key is created
               with index = self.last_[change|payout]_index + 1
        
        Returns:
            str: A bitcoin address
        """
        # Always do compressed keys
        return self.get_public_key(change, n).address(True, self.testnet)

    def get_next_address(self, change):
        """ Returns the next public address in the specified chain

        Args:
            change (bool): If True, returns an address for change purposes,
               otherwise returns an address for payment.

        Returns:
            str: A bitcoin address
        """
        return self.get_address(change)

    def get_utxo(self):
        """ Gets all unspent transactions associated with all addresses
            up to and including the last known indices for both change
            and payout chains.
        """
        k = self.key.public_key if isinstance(self.key, HDPrivateKey) else self.key
        return self.txn_provider.get_utxo_hd(pub_key=k,
                                             last_payout_index=self.last_indices[self.PAYOUT_CHAIN],
                                             last_change_index=self.last_indices[self.CHANGE_CHAIN])
    
    def to_dict(self):
        """ Returns a JSON-serializable dict to save account data

        Returns:
            dict: Dict that can be serialized into a JSON string
        """
        # For now just return the pub-key and indices of last
        # change and payout addresses.
        pub_key = self.key if isinstance(self.key, HDPublicKey) else self.key.public_key
        return { "public_key": pub_key.to_b58check(self.testnet),
                 "last_payout_index": self.last_indices[self.PAYOUT_CHAIN],
                 "last_change_index": self.last_indices[self.CHANGE_CHAIN],
             }

    @property
    def balance(self):
        """ Returns balances, both for confirmed and unconfirmed transactions,
            for this account.

        Returns:
            tuple: First item is the balance for confirmed transactions and
               second item is the balance for unconfirmed transactions
        """
        pub_key = self.key if isinstance(self.key, HDPublicKey) else self.key.public_key        
        address_balances = self.txn_provider.get_balance_hd(pub_key=pub_key,
                                                            last_payout_index=self.last_indices[self.PAYOUT_CHAIN],
                                                            last_change_index=self.last_indices[self.CHANGE_CHAIN])

        balance = [0, 0] # (confirmed, unconfirmed)
        for k, v in address_balances.items():
            balance[0] += v[0]
            balance[1] += v[1]

        return tuple(balance)
            
    @property
    def all_used_addresses(self):
        """ List of all used addresses

        Returns:
            list(str): list of all used addresses (Base58Check encoded)
        """
        return self._used_addresses[self.PAYOUT_CHAIN] + self._used_addresses[self.CHANGE_CHAIN]

    @property
    def current_change_address(self):
        """ Returns the current change address

        Returns:
            str: Base58Check-encoded string containing the current 
               change address.
        """
        return self.get_address(True, self.last_indices[self.CHANGE_CHAIN])

    @property
    def current_payout_address(self):
        """ Returns the current payout address

        Returns:
            str: Base58Check-encoded string containing the current 
               payout address.
        """
        return self.get_address(False, self.last_indices[self.PAYOUT_CHAIN])
