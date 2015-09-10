import json

from two1.bitcoin.crypto import HDKey, HDPrivateKey, HDPublicKey
from two1.bitcoin.script import Script
from two1.bitcoin.txn import Transaction, TransactionInput, TransactionOutput
from two1.bitcoin import utils
from two1.wallet import exceptions
from two1.wallet.account_types import account_types
from two1.wallet.hd_account import HDAccount
from two1.wallet.base_wallet import BaseWallet
from two1.wallet.utxo_selectors import utxo_selector_smallest_first

DEFAULT_ACCOUNT_TYPE = 'BIP32'

class Two1Wallet(BaseWallet):
    """ An HD wallet class capable of handling multiple types of wallets.

        This wallet can implement a variety of account types, including:
        pure BIP-32, pure BIP-44, Hive, and Mycelium variants.

        This class depends on pluggable elements which allow flexibility to use
        different backend data providers (bitcoind, chain.com, etc.) as well
        as different UTXO selection algorithms. In particular, these elements
        are:

        1. A transaction data provider class that implements the abstract
           class found in TxnDataProvider.
        2. A unspent transaction output selector (utxo_selector):

        utxo_selector should be a filtering function with prototype:
            selected, fees = utxo_selector_func(txn_data_provider,
                                                list(UnspentTransactionOutput),
                                                int, int)

        The job of the selector is to choose from the input list of UTXOs which
        are to be used in a transaction such that there are sufficient coins
        to pay the total amount (3rd passed argument) and transaction fees.
        Since transaction fees are computed based on size of transaction, which
        is in turn (partially) determined by number of inputs and number of
        outputs (4th passed argument), the selector must determine the required
        fees and return that amount as well.

        The return value must be a tuple where the first item is a dict keyed
        by address with a list of selected UnspentTransactionOutput objects and
        the second item is the fee amount (in satoshis).

        This is pluggable to allow for different selection criteria, i.e. fewest
        number of inputs, oldest UTXOs first, newest UTXOs first, minimize change
        amount, etc.

    Args:
        config (dict): A dict containing at minimum a "master_key" key with a 
           Base58Check encoded HDPrivateKey as the value.
        txn_data_provider (TransactionDataProvider): An instance of a derived
           TransactionDataProvider class as described above.
        utxo_selector (function): A filtering function with the prototype documented
           above.

    Returns:
        Two1Wallet: The wallet instance.
    """
    DUST_LIMIT = 5460 # Satoshis - should this be somewhere else?

    @staticmethod
    def create(txn_data_provider,
               passphrase='',
               utxo_selector=utxo_selector_smallest_first,
               testnet=False):
        """ Creates a Two1Wallet using a random seed.

            This will create a wallet using the default account type (currently BIP32).
        
        Args:
            txn_data_provider (TransactionDataProvider): An instance of a derived
               TransactionDataProvider class as described above.
            passphrase (str): A passphrase to lock the wallet with.
            utxo_selector (function): A filtering function with the prototype documented
               above.
            testnet (bool): Whether or not this wallet will be used for testnet.

        Returns:
            Two1Wallet: The wallet instance.
        """
        # Create:
        # 1. master key seed + mnemonic
        # 2. First account
        # Store info to file
        account_type = "BIP44Testnet" if testnet else DEFAULT_ACCOUNT_TYPE
        master_key, mnemonic = HDPrivateKey.master_key_from_entropy(passphrase)
        config = { "master_key": master_key.to_b58check(testnet),
                   "master_seed": mnemonic,
                   "account_type": account_type
               }
        wallet = Two1Wallet(config, txn_data_provider, utxo_selector)

        return wallet

    @staticmethod
    def import_from_mnemonic(txn_data_provider, mnemonic,
                             passphrase='',
                             utxo_selector=utxo_selector_smallest_first,
                             account_type=DEFAULT_ACCOUNT_TYPE):
        """ Creates a Two1Wallet from an existing mnemonic.

        Args:
            txn_data_provider (TransactionDataProvider): An instance of a derived
               TransactionDataProvider class as described above.
            mnemonic (str): The mnemonic representing the wallet seed.
            passphrase (str): A passphrase to lock the wallet with.
            utxo_selector (function): A filtering function with the prototype documented
               above.
            account_type (str): One of the account types in account_types.py.

        Returns:
            Two1Wallet: The wallet instance.
        """
        
        if account_type not in account_types:
            raise ValueError("account_type must be one of %r" % account_types.keys())

        testnet = account_type == "BIP44Testnet"
        master_key = HDPrivateKey.master_key_from_mnemonic(mnemonic, passphrase)
        config = { "master_key": master_key.to_b58check(testnet),
                   "master_seed": mnemonic,
                   "account_type": account_type
               }
        wallet = Two1Wallet(config, txn_data_provider, utxo_selector)
        wallet.discover_accounts()

        return wallet
        
    def __init__(self, config, txn_data_provider, utxo_selector=utxo_selector_smallest_first):
        self.txn_data_provider = txn_data_provider
        self.utxo_selector = utxo_selector
        self._testnet = False
        
        m = config.get('master_key', None)
        if m is not None:
            self._master_key = HDKey.from_b58check(m)
            self._master_seed = config.get('master_seed')
            assert isinstance(self._master_key, HDPrivateKey)
            assert self._master_key.master
        else:
            raise ValueError("config does not have a required key: 'master_key'")

        acct_type = config.get('account_type', None)
        if acct_type is not None:
            self.account_type = account_types[acct_type]
            self._testnet = self.account_type == 'BIP44Testnet'
        else:
            raise ValueError("config does not have a required key: 'account_type'")

        self._root_keys = HDKey.from_path(self._master_key, self.account_type.account_derivation_prefix)

        self._accounts = []
        self._account_map = {}

        account_config = config.get("accounts", None)
        if account_config is None:
            # Create default account
            self._init_account(0, "default")
        else:
            # Setup the account map first
            self._account_map = config.get("account_map", {})
            self._load_accounts(account_config)

    def discover_accounts(self):
        """ Discovers all accounts associated with the wallet.

            Account discovery is accomplished by the discovery procedure outlined
            in BIP44. Namely, we start with account 0', check to see if there are
            used addresses. If there are, we continue to account 1' and proceed
            until the first account with no used addresses.

            The discovered accounts are stored internally, but can be retrieved with
            the Two1Wallet.accounts property.
        """
        has_txns = True
        i = 0
        while has_txns:
            if i >= len(self._accounts):
                self._init_account(i)
            has_txns = self._accounts[i].has_txns()
            i += 1

        # The last one will not have txns, so remove it unless it's the
        # default one.
        if len(self._accounts) > 1:
            del self._accounts[-1]
            
    def _init_account(self, index, name=""):
        # Account keys use hardened deriviation, so make sure the MSB is set
        acct_index = index | 0x80000000
        
        acct_priv_key = HDPrivateKey.from_parent(self._root_keys[-1], acct_index)
        acct = HDAccount(acct_priv_key, name, acct_index, self.txn_data_provider, self._testnet)
        self._accounts.insert(index, acct)
        self._account_map[name] = index
        
    def _load_accounts(self, account_config):
        for i, a in enumerate(account_config):
            # Determine account name
            name = self.get_account_name(i)
            self._init_account(i, name)

            acct = self._accounts[i]

            # Make sure that the key serialization in the config matches
            # that from our init
            if a["public_key"] != self.accounts[i].key.public_key.to_b58check(self._testnet):
                raise ValueError("Account config inconsistency detected: pub key for account %d (%s) does not match expected." % (i, name))

    def _check_and_get_accounts(self, accounts):
        accts = []
        if not accounts:
            accts = self._accounts
        else:
            for a in accounts:
                if isinstance(a, int):
                    if a < 0 or a >= len(self._accounts):
                        raise ValueError("Specified account (%d) does not exist." % a)
                    else:
                        accts.append(self._accounts[a])
                elif isinstance(a, str):
                    account_index = self._account_map.get(a, None)
                    if account_index is not None:
                        accts.append(self._accounts[account_index])
                    else:
                        raise ValueError("Specified account (%s) does not exist." % a)
                elif isinstance(a, HDAccount) and a in self._accounts:
                    accts.append(a)
                else:
                    raise TypeError("account (%r) must be either a string or an int" % a)

        return accts

    def _get_private_keys(self, addresses):
        """ Returns private keys for a list of addresses, if they
            are a part of this wallet.
        """
        address_paths = self.find_addresses(addresses)
        private_keys = {}
        for addr, path in address_paths.items():
            account_index = path[0]
            if account_index >= 0x8000000:
                account_index &= 0x7fffffff
            acct = self._accounts[account_index]
            private_keys[addr] = acct.get_private_key(path[1], path[2])

        return private_keys

    def find_addresses(self, addresses):
        """ Returns the paths to the address, if found. 
        
            All *discovered* accounts are checked. Within an account, all
            addresses up to GAP_LIMIT (20) addresses beyond the last known
            index for the chain are checked.

        Args:
            addresses (list(str)): list of Base58Check encoded addresses.

        Returns:
            dict: Dict keyed by address with the path (account index first)
               corresponding to the derivation path for that key.
        """
        addrs = addresses
        found = {}
        for acct in self._accounts:
            acct_found = acct.find_addresses(addrs)
            found.update(acct_found)
            # Remove any found addresses so we don't keep searching for them
            remove_indices = sorted(list(acct_found.keys()), reverse=True)
            for r in remove_indices:
                addrs.remove(r)

        # Do we also check 1 account up, just in case this was imported somewhere
        # else and that created the next account? That could go on forever though...
                
        return found
    
    def address_belongs(self, address):
        """ Returns the full path for generating this address

        Args:
            address (str): Base58Check encoded bitcoin address.
        
        Returns:
            str or None: The full key derivation path if found. Otherwise,
               returns None.
        """
        found = self.find_addresses([address])

        if address in found:
            return self.account_type.account_derivation_prefix + "/" + \
                HDKey.path_from_indices([found[address][0],
                                         found[address][1],
                                         found[address][2]])
        else:
            return None
        
    def get_account_name(self, index):
        """ Returns the account name for the given index.

        Note:
            The name of the account is a convenience item only - it
            serves no purpose other than being a human-readable
            identifier.

        Args:
            index (int): The index of the account to retrieve the
               name for.

        Returns:
            str or None: The name of the account if found, or None.
        """
        for name, i in self._account_map.items():
            if index == i:
                return name

        return None

    def get_utxo(self, accounts=[]):
        """ Returns all UTXOs for all addresses in all specified accounts.

        Args:
            accounts (list): A list of either account indices or names.

        Returns:
            dict: A dict keyed by address containing a list of UnspentTransactionOutput
               objects for that address. Only addresses for which there 
               are current UTXOs are included.
        """
        utxos = {}
        for acct in self._check_and_get_accounts(accounts):
            utxos.update(acct.get_utxo())

        return utxos

    def to_dict(self):
        """ Creates a dict of critical configuration parameters.

        Returns:
            dict: A dict containing key/value pairs that is JSON serializable.
        """
        config = { "master_key": self._master_key.to_b58check(self._testnet),
                   "master_seed": self._master_seed,
                   "account_map": self._account_map,
                   "accounts": [acct.to_dict() for acct in self._accounts]
            }
        return config

    @property
    def addresses(self):
        """ Gets the address list for the current wallet.
        
        Returns:
            list(str): The current list of addresses in this wallet.
        """
        addresses = []
        for a in self._accounts:
            addresses += a.all_used_addresses

        return addresses
    
    @property
    def current_address(self):
        """ Gets the preferred address.

        Returns:
            str: The current preferred payment address. 
        """
        return self.get_new_payout_address()
    
    def get_new_payout_address(self, account_name_or_index=None):
        """ Gets the next payout address.

        Args:
            account_name_or_index (str or int): The account to retrieve the
               payout address from. If not provided, the default account (0')
               is used.

        Returns:
            str: A Base58Check encoded bitcoin address.
        """
        if account_name_or_index is None:
            acct = self._accounts[0]
        else:
            acct = self._check_and_get_accounts([account_name_or_index])[0]

        return acct.get_next_address(False)

    def broadcast_transaction(self, tx):
        """ Broadcasts the transaction to the Bitcoin network.

        Args:
            tx (str): Hex string serialization of the transaction 
               to be broadcasted to the Bitcoin network..
        Returns:
            str: The name of the transaction that was broadcasted.
        """
        res = []
        try:
            txid = self.txn_data_provider.send_transaction(tx)
            res = [{"txid": txid, "txn": tx}]
        except exceptions.WalletError as e:
            print("Problem sending transaction to network: %s" % e)

        return res
        
    def send_to_multiple(self, addresses_and_amounts, accounts=[]):
        """ Sends bitcoins to multiple addresses.

        Args:
            addresses_and_amounts (dict): A dict keyed by recipient address
               and corresponding values being the amount - *in satoshis* - to
               send to that address.
            accounts (list(str or int)): List of accounts to use. If not provided,
               all discovered accounts may be used based on the chosen UTXO
               selection algorithm.

        Returns:
            str or None: A string containing the submitted TXID or None.
        """
        total_amount = sum([amt for amt in addresses_and_amounts.values()])

        if not accounts:
            accts = self._accounts
        else:
            accts = self._check_and_get_accounts(accounts)
        
        # Now get the unspents from all accounts and select which we
        # want to use
        utxos_by_addr = self.get_utxo(accts)
                
        selected_utxos, fees = self.utxo_selector(txn_data_provider=self.txn_data_provider,
                                                  utxos_by_addr=utxos_by_addr,
                                                  amount=total_amount,
                                                  num_outputs=len(addresses_and_amounts))

        total_with_fees = total_amount + fees
        
        # Verify we have enough money
        if total_with_fees > self.confirmed_balance(): # First element is confirmed balance
            return False

        # Get all private keys in one shot
        private_keys = self._get_private_keys(list(selected_utxos.keys()))
        
        # Build up the transaction
        inputs = []
        outputs = []
        total_utxo_amount = 0
        for addr, utxo_list in selected_utxos.items():
            for utxo in utxo_list:
                total_utxo_amount += utxo.value
                inputs.append(TransactionInput(outpoint=utxo.transaction_hash,
                                               outpoint_index=utxo.outpoint_index,
                                               script=utxo.script,
                                               sequence_num=0xffffffff))

        for addr, amount in addresses_and_amounts.items():
            _, key_hash = utils.address_to_key_hash(addr)
            outputs.append(TransactionOutput(value=amount,
                                             script=Script.build_p2pkh(key_hash)))

        # one more output for the change, if the change is above the dust limit
        change = total_utxo_amount - total_with_fees
        if change > self.DUST_LIMIT:
            _, change_key_hash = utils.address_to_key_hash(accts[0].get_next_address(True))
            outputs.append(TransactionOutput(value=change,
                                             script=Script.build_p2pkh(change_key_hash)))

        txn = Transaction(version=Transaction.DEFAULT_TRANSACTION_VERSION,
                          inputs=inputs,
                          outputs=outputs,
                          lock_time=0)

        # Now sign all the inputs
        i = 0
        for addr, utxo_list in selected_utxos.items():
            # Need to get the private key
            private_key = private_keys.get(addr, None)
            if private_key is None:
                raise exceptions.WalletSigningError("Couldn't find address %s or unable to generate private key for it." % addr)

            for utxo in utxo_list:
                signed = txn.sign_input(input_index=i,
                                        hash_type=Transaction.SIG_HASH_ALL,
                                        private_key=private_key,
                                        sub_script=utxo.script)

                if not signed:
                    raise exceptions.WalletSigningError("Unable to sign input %d." % i)

                i += 1

        # Was able to sign all inputs, now send txn
        return self.broadcast_transaction(utils.bytes_to_str(bytes(txn)))

    def send_to(self, address, amount, accounts=[]):
        """ Sends Bitcoin to the provided address for the specified amount.

        Args:
            address (str): The address to send the Bitcoin too.
            amount (number): The amount of Bitcoin to send.
            accounts (list(str or int)): List of accounts to use. If not provided,
               all discovered accounts may be used based on the chosen UTXO
               selection algorithm.

        Returns:
            list(dict): A list of dicts containing transaction names and raw transactions.
               e.g.: [{"txid": txid0, "txn": txn_hex0}, ...]
        """
        return self.send_to_multiple({address: amount})
        
    @property
    def balances(self):
        """ Balance for the wallet.
        
        Returns:
            tuple: First element is confirmed balance, second is unconfirmed.
        """
        balances = [0, 0]
        for acct in self._accounts:
            acct_balance = acct.balance
            balances[0] += acct_balance[0]
            balances[1] += acct_balance[1]

        return tuple(balances)

    def confirmed_balance(self):
        """ Gets the current confirmed balance of the wallet in Satoshi.

        Returns:
            number: The current confirmed balance.
        """
        return self.balances[0]
    	
    def unconfirmed_balance(self):
        """ Gets the current unconfirmed balance of the wallet in Satoshi.

        Returns:
            number: The current unconfirmed balance.
        """
        return self.balances[1]

    @property
    def accounts(self):
        """ All accounts in the wallet.

        Returns:
            list(HDAccount): List of HDAccount objects.
        """
        return self._accounts

    
