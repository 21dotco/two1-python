import getpass
import json
import logging

import base64
import os
import pyaes
from jsonrpcclient.exceptions import ReceivedErrorResponse
from pbkdf2 import PBKDF2
from two1.lib.bitcoin.crypto import HDKey
from two1.lib.bitcoin.crypto import HDPrivateKey
from two1.lib.bitcoin.crypto import HDPublicKey
from two1.lib.bitcoin.crypto import PublicKey
from two1.lib.bitcoin.script import Script
from two1.lib.bitcoin.txn import Transaction
from two1.lib.bitcoin.txn import TransactionInput
from two1.lib.bitcoin.txn import TransactionOutput
from two1.lib.bitcoin import utils
from two1.lib.blockchain.base_provider import BaseProvider
from two1.lib.blockchain.twentyone_provider import TwentyOneProvider
from two1.lib.wallet import exceptions
from two1.lib.wallet.account_types import account_types
from two1.lib.wallet.hd_account import HDAccount
from two1.lib.wallet.base_wallet import BaseWallet
from two1.lib.wallet.exceptions import AccountCreationError
from two1.lib.wallet.utxo_selectors import DEFAULT_INPUT_FEE
from two1.lib.wallet.utxo_selectors import DEFAULT_OUTPUT_FEE
from two1.lib.wallet.socket_rpc_server import UnixSocketServerProxy
from two1.lib.wallet.utxo_selectors import utxo_selector_smallest_first


class Two1Wallet(BaseWallet):
    """ An HD wallet class capable of handling multiple types of wallets.

        This wallet can implement a variety of account types, including:
        pure BIP-32, pure BIP-44, Hive, and Mycelium variants.

        This class depends on pluggable elements which allow flexibility to use
        different backend data providers (bitcoind, chain.com, etc.) as well
        as different UTXO selection algorithms. In particular, these elements
        are:

        1. A bitcoin data provider class that implements the abstract
           class found in two1.blockchain.BaseProvider.
        2. A unspent transaction output selector (utxo_selector):

        utxo_selector should be a filtering function with prototype:
            selected, fees = utxo_selector_func(data_provider,
                                                list(UnspentTransactionOutput),
                                                int, int, fees=None)

        The job of the selector is to choose from the input list of UTXOs which
        are to be used in a transaction such that there are sufficient coins
        to pay the total amount (3rd passed argument) and transaction fees.
        Since transaction fees are computed based on size of transaction, which
        is in turn (partially) determined by number of inputs and number of
        outputs (4th passed argument), the selector must determine the required
        fees and return that amount as well, unless fees (5th passed argument)
        is not None in which case the application is specifiying the fees.

        The return value must be a tuple where the first item is a dict keyed
        by address with a list of selected UnspentTransactionOutput objects and
        the second item is the fee amount (in satoshis).

        This is pluggable to allow for different selection criteria,
        i.e. fewest number of inputs, oldest UTXOs first, newest UTXOs
        first, minimize change amount, etc.

    Args:
        params (dict): A dict containing at minimum a "master_key" key
           with a Base58Check encoded HDPrivateKey as the value.
        data_provider (BaseProvider): An instance of a derived
           two1.blockchain.BaseProvider class as described above.
        passphrase (str): Passphrase to unlock wallet key if it is locked.
        utxo_selector (function): A filtering function with the
           prototype documented above.

    Returns:
        Two1Wallet: The wallet instance.
    """
    DUST_LIMIT = 546  # Satoshis - should this be somewhere else?
    AES_BLOCK_SIZE = 16
    DEFAULT_ACCOUNT_TYPE = 'BIP32'
    DEFAULT_WALLET_PATH = os.path.join(os.path.expanduser('~'),
                                       ".two1",
                                       "wallet",
                                       "default_wallet.json")
    WALLET_FILE_VERSION = "0.1.0"
    WALLET_CACHE_VERSION = "0.1.0"

    """ The configuration options available for creating the wallet.

        The keys of this dictionary are the available configuration
        settings/options for the wallet. The value for each key
        represents the possible values for each option.
        e.g. {key_style: ["HD","Brain","Simple"], ....}
    """
    config_options = {"account_type": account_types.keys(),
                      "passphrase": "",
                      "data_provider": BaseProvider,
                      "testnet": [True, False],
                      "wallet_path": ""}

    required_params = ['master_key', 'locked', 'key_salt', 'passphrase_hash',
                       'account_type']
    logger = logging.getLogger('wallet')

    @staticmethod
    def is_locked(wallet_path=DEFAULT_WALLET_PATH):
        """ Returns whether a wallet is locked with a passphrase.

        Returns:
            bool: True if the wallet has been locked with a
                passphrase, False otherwise.
        """
        locked = False
        if os.path.exists(wallet_path):
            with open(wallet_path, 'r') as f:
                params = json.load(f)
                locked = params.get('locked', False)
        else:
            error = "Wallet does not exist at %s!" % wallet_path
            Two1Wallet.logger.error(error)
            raise exceptions.WalletError(error)

        return locked

    @staticmethod
    def check_wallet_file(wallet_path=DEFAULT_WALLET_PATH):
        """ Returns whether the specified wallet file exists and
            contains the minimum set of parameters required to load
            the wallet.

        Returns:
            bool: True if the wallet file exists and is ready to use,
                False otherwise.

        """
        if os.path.exists(wallet_path):
            # Check if the config is actually good
            params = {}
            with open(wallet_path, 'r') as f:
                params = json.load(f)

            for rp in Two1Wallet.required_params:
                if rp not in params:
                    return False

            return True
        else:
            return False

    @staticmethod
    def is_configured():
        """ Returns the configuration/initialization status of the
            wallet.

        Returns:
            bool: True if the default wallet has been configured and
                ready to use otherwise False
        """
        return Two1Wallet.check_wallet_file()

    @staticmethod
    def configure(config_options):
        """ Creates a default wallet.

            If 'wallet_path' is found in config_options, the wallet is
            stored at that location. Otherwise, it is created in
            ~/.two1/wallet/default_wallet.json.

        Args:
            config_options (dict): A dict of config options, the keys
                and allowed values of each key are found in the class
                variable of the same name.

        Returns:
            bool: True if the wallet was created and written to disk,
                False otherwise.
        """
        wallet_path = config_options.get('wallet_path',
                                         Two1Wallet.DEFAULT_WALLET_PATH)
        wallet_dirname = os.path.dirname(wallet_path)
        if not os.path.exists(wallet_dirname):
            os.makedirs(wallet_dirname)
        else:
            if os.path.exists(wallet_path):
                Two1Wallet.logger.error(
                    "File %s already present. Not creating wallet." %
                    wallet_path)
                return False

        dp = config_options.get('data_provider', None)
        account_type = config_options.get('account_type', Two1Wallet.DEFAULT_ACCOUNT_TYPE)
        passphrase = config_options.get('passphrase', "")
        testnet = config_options.get('testnet', False)

        rv = None
        if dp is None or not isinstance(dp, BaseProvider):
            rv = False
        else:
            wallet = Two1Wallet.create(data_provider=dp,
                                       passphrase=passphrase,
                                       account_type=account_type,
                                       testnet=testnet)

            wallet.discover_accounts()
            wallet.to_file(wallet_path)

            rv = os.path.exists(wallet_path)

        return rv

    @staticmethod
    def _encrypt_str(s, key):
        iv = utils.rand_bytes(Two1Wallet.AES_BLOCK_SIZE)
        encrypter = pyaes.Encrypter(pyaes.AESModeOfOperationCBC(key, iv = iv))
        msg_enc = encrypter.feed(str.encode(s))
        msg_enc += encrypter.feed()
        return base64.b64encode(iv + msg_enc).decode('ascii')

    @staticmethod
    def _decrypt_str(enc, key):
        enc_bytes = base64.b64decode(enc)
        iv = enc_bytes[:Two1Wallet.AES_BLOCK_SIZE]
        decrypter = pyaes.Decrypter(pyaes.AESModeOfOperationCBC(key, iv = iv))
        dec = decrypter.feed(enc_bytes[Two1Wallet.AES_BLOCK_SIZE:])
        dec += decrypter.feed()
        return dec.rstrip(b'\x00').decode('ascii')

    @staticmethod
    def encrypt(master_key, master_seed, passphrase, key_salt):
        key = PBKDF2(passphrase, key_salt).read(Two1Wallet.AES_BLOCK_SIZE)

        master_key_enc = Two1Wallet._encrypt_str(master_key, key)
        master_seed_enc = Two1Wallet._encrypt_str(master_seed, key)

        return (master_key_enc, master_seed_enc)

    @staticmethod
    def decrypt(master_key_enc, master_seed_enc, passphrase, key_salt):
        key = PBKDF2(passphrase, key_salt).read(Two1Wallet.AES_BLOCK_SIZE)

        master_key = Two1Wallet._decrypt_str(master_key_enc, key)
        master_seed = Two1Wallet._decrypt_str(master_seed_enc, key)

        return (master_key, master_seed)

    @staticmethod
    def create(data_provider,
               passphrase='',
               account_type=DEFAULT_ACCOUNT_TYPE,
               utxo_selector=utxo_selector_smallest_first,
               testnet=False):
        """ Creates a Two1Wallet using a random seed.

            This will create a wallet using the default account type
            (currently BIP32).

        Args:
            data_provider (BaseProvider): An instance of a derived
                two1.blockchain.BaseProvider class as described above.
            passphrase (str): A passphrase to lock the wallet with.
            account_type (str): One of the account types in account_types.py.
            utxo_selector (function): A filtering function with the
                prototype documented above.
            testnet (bool): Whether or not this wallet will be used
                for testnet.

        Returns:
            tuple(Two1Wallet, mnemonic): The wallet instance and the mnemonic
        """
        # Create:
        # 1. master key seed + mnemonic
        # 2. First account
        # Store info to file
        account_type = "BIP44Testnet" if testnet else account_type
        master_key, mnemonic = HDPrivateKey.master_key_from_entropy(passphrase)
        passphrase_hash = PBKDF2.crypt(passphrase)
        key_salt = utils.rand_bytes(8)

        master_key_b58 = master_key.to_b58check(testnet)
        if passphrase:
            mkey, mseed = Two1Wallet.encrypt(master_key=master_key_b58,
                                             master_seed=mnemonic,
                                             passphrase=passphrase,
                                             key_salt=key_salt)
        else:
            mkey = master_key_b58
            mseed = mnemonic

        config = {"master_key": mkey,
                  "master_seed": mseed,
                  "passphrase_hash": passphrase_hash,
                  "key_salt": utils.bytes_to_str(key_salt),
                  "locked": bool(passphrase),
                  "account_type": account_type}
        wallet = Two1Wallet(config, data_provider, passphrase, utxo_selector)

        return wallet

    @staticmethod
    def import_from_mnemonic(data_provider, mnemonic,
                             passphrase='',
                             utxo_selector=utxo_selector_smallest_first,
                             account_type=DEFAULT_ACCOUNT_TYPE):
        """ Creates a Two1Wallet from an existing mnemonic.

        Args:
            data_provider (BaseProvider): An instance of a derived
                two1.blockchain.BaseProvider class as described above.
            mnemonic (str): The mnemonic representing the wallet seed.
            passphrase (str): A passphrase to lock the wallet with.
            utxo_selector (function): A filtering function with the
                prototype documented above.
            account_type (str): One of the account types in account_types.py.

        Returns:
            Two1Wallet: The wallet instance.
        """

        if account_type not in account_types:
            raise ValueError("account_type must be one of %r" %
                             account_types.keys())

        testnet = account_type == "BIP44Testnet"
        master_key = HDPrivateKey.master_key_from_mnemonic(mnemonic,
                                                           passphrase)
        passphrase_hash = PBKDF2.crypt(passphrase)
        key_salt = utils.rand_bytes(8)

        master_key_b58 = master_key.to_b58check(testnet)
        if passphrase:
            mkey, mseed = Two1Wallet.encrypt(master_key=master_key_b58,
                                             master_seed=mnemonic,
                                             passphrase=passphrase,
                                             key_salt=key_salt)
        else:
            mkey = master_key_b58
            mseed = mnemonic

        config = {"master_key": mkey,
                  "master_seed": mseed,
                  "passphrase_hash": passphrase_hash,
                  "key_salt": utils.bytes_to_str(key_salt),
                  "locked": bool(passphrase),
                  "account_type": account_type}

        wallet = Two1Wallet(config, data_provider, passphrase, utxo_selector)
        wallet.discover_accounts()

        return wallet

    def __init__(self, params_or_file, data_provider,
                 passphrase='',
                 utxo_selector=utxo_selector_smallest_first):
        self.data_provider = data_provider
        self.utxo_selector = utxo_selector
        self._testnet = False
        self._filename = ""

        params = {}
        if isinstance(params_or_file, dict):
            params = params_or_file
        elif isinstance(params_or_file, str):
            # Assume it's a filename
            with open(params_or_file, 'r') as f:
                params = json.load(f)
                self._filename = params_or_file
        else:
            raise TypeError("params_or_file must either be a JSON-serializable dict or a file path.")

        for rp in self.required_params:
            if rp not in params:
                raise ValueError("params does not have a required key: '%s'" % rp)

        # Keep these around for writing out using to_file()
        self._orig_params = params

        if passphrase:
            # Make sure the passphrase is correct
            if params['passphrase_hash'] != PBKDF2.crypt(passphrase, params['passphrase_hash']):
                raise exceptions.PassphraseError("Given passphrase is incorrect.")

        if params['locked']:
            mkey, self._master_seed = self.decrypt(master_key_enc=params['master_key'],
                                                   master_seed_enc=params['master_seed'],
                                                   passphrase=passphrase,
                                                   key_salt=bytes.fromhex(params['key_salt']))

            self._master_key = HDKey.from_b58check(mkey)

        else:
            self._master_key = HDKey.from_b58check(params['master_key'])
            self._master_seed = params['master_seed']

        assert isinstance(self._master_key, HDPrivateKey)
        assert self._master_key.master

        acct_type = params.get('account_type', None)
        self.account_type = account_types[acct_type]
        self._testnet = self.account_type == account_types['BIP44Testnet']
        self.data_provider.testnet = self._testnet

        self._root_keys = HDKey.from_path(self._master_key,
                                          self.account_type.account_derivation_prefix)

        self._accounts = []
        self._account_map = {}

        account_params = params.get("accounts", None)
        cache_file = params.get("cache_file", None)
        if account_params is None:
            # Create default account
            self._init_account(0, "default")
        else:
            # Setup the account map first
            self._account_map = params.get("account_map", {})
            self._load_accounts(account_params, cache_file)

        if self.logger.level == logging.DEBUG:
            for a in self._accounts:
                kser = ""
                if isinstance(a.key, HDPrivateKey):
                    kser = a.key.public_key.to_b58check(self._testnet)
                else:
                    kser = a.key.to_b58check(self._testnet)

                self.logger.debug("Account %d (%s) public key: %s" %
                                  (a.index & 0x7fffffff, a.name, kser))

    @property
    def testnet(self):
        """ Getter testnet property
        """
        return self._testnet

    def discover_accounts(self):
        """ Discovers all accounts associated with the wallet.

            Account discovery is accomplished by the discovery
            procedure outlined in BIP44. Namely, we start with account
            0', check to see if there are used addresses. If there
            are, we continue to account 1' and proceed until the first
            account with no used addresses.

            The discovered accounts are stored internally, but can be
            retrieved with the Two1Wallet.accounts property.
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

    def create_account(self, name):
        """ Creates an account.

        Note:
            Account creation may fail if:
            1. There is an existing account that has no transactions
               associated with it as creating a new account would
               violate the BIP-44 account discovery protocol:

               https://github.com/bitcoin/bips/blob/master/bip-0044.mediawiki#Account_discovery
            2. There is an existing account with the same name.

        Args:
            name (str): The name of the account.

        Returns:
            bool: True if account creation was successful, False otherwise.
        """
        rv = False
        last_index = len(self._accounts) - 1

        if name in self._accounts:
            if self._accounts[last_index].has_txns():
                self._init_account(index=last_index + 1,
                                   name=name)
                rv = name in self._account_map
            else:
                raise AccountCreationError("The last account (name: '%s', index: %d) has no transactions. Cannot create new account." %
                                           self._accounts.name,
                                           last_index)
        else:
            raise AccountCreationError("An account named '%s' already exists." % name)

        return rv

    def _init_account(self, index, name="", account_state=None):
        # Account keys use hardened deriviation, so make sure the MSB is set
        acct_index = index | 0x80000000

        acct_priv_key = HDPrivateKey.from_parent(self._root_keys[-1],
                                                 acct_index)
        acct = HDAccount(hd_key=acct_priv_key,
                         name=name,
                         index=acct_index,
                         data_provider=self.data_provider,
                         testnet=self._testnet,
                         last_state=account_state)
        self._accounts.insert(index, acct)
        self._account_map[name] = index

    def _load_accounts(self, account_params, cache_file=None):
        cache = {}
        if cache_file is not None and os.path.exists(cache_file):
            with open(cache_file) as cf:
                cache = json.load(cf)

        for i, a in enumerate(account_params):
            # Determine account name
            state = {"last_payout_index": a["last_payout_index"],
                     "last_change_index": a["last_change_index"]}

            if "addresses" in cache:
                state["addresses"] = {int(k): {int(ik): iv for ik, iv in v.items()}
                                      for k, v in cache["addresses"][i].items()}
            if "transactions" in cache:
                state["transactions"] = cache["transactions"][i]

            name = self.get_account_name(i)
            self._init_account(i, name, state)

            # Make sure that the key serialization in the params matches
            # that from our init
            if a["public_key"] != self.accounts[i].key.public_key.to_b58check(self._testnet):
                raise ValueError("Account params inconsistency detected: pub key for account %d (%s) does not match expected." % (i, name))

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

    def _update_account_balances(self):
        for a in self._accounts:
            a._update_balance()

    def get_private_keys(self, addresses):
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

    def get_private_key(self, address):
        """ Returns the private key corresponding to address, if it is
            a part of this wallet.

        Args:
            address (str): A Base58Check encoded bitcoin address

        Returns:
            PrivateKey: A private key object or None.
        """
        pkeys = self.get_private_keys([address])
        return pkeys[address] if address in pkeys else None

    def get_private_for_public(self, public_key):
        """ Returns the private key for the given public_key, if it is
            a part of this wallet.

        Args:
            public_key (PublicKey): The public key object to retrieve
                the private key for.

        Returns:
            PrivateKey: A private key object or None.
        """
        return self.get_private_key(public_key.address(testnet=self._testnet))

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

        # Do we also check 1 account up, just in case this was
        # imported somewhere else and that created the next account?
        # That could go on forever though...

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

    def get_utxos(self, accounts=[]):
        """ Returns all UTXOs for all addresses in all specified accounts.

        Args:
            accounts (list): A list of either account indices or names.

        Returns:
            dict: A dict keyed by address containing a list of
               UnspentTransactionOutput objects for that address. Only
               addresses for which there are current UTXOs are
               included.
        """
        utxos = {}
        for acct in self._check_and_get_accounts(accounts):
            utxos.update(acct.get_utxos())

        return utxos

    def to_dict(self):
        """ Creates a dict of critical parameters.

        Returns:
            dict: A dict containing key/value pairs that is JSON serializable.
        """
        params = self._orig_params.copy()
        params["version"] = self.WALLET_FILE_VERSION
        params["account_map"] = self._account_map
        params["accounts"] = [acct.to_dict() for acct in self._accounts]

        return params

    def to_file(self, file_or_filename):
        """ Writes all wallet information to a file.
        """
        address_cache = [a.address_cache for a in self._accounts]
        txn_cache = [a.transaction_cache for a in self._accounts]
        cache = {"version": self.WALLET_CACHE_VERSION,
                 "addresses": address_cache,
                 "transactions": txn_cache}

        if isinstance(file_or_filename, str):
            f = file_or_filename
        else:
            f = file_or_filename.name
        dirname = os.path.dirname(f)

        p = self.to_dict()
        # Convert to hex str to make sure we don't get weird
        # characters.
        cf_id = utils.bytes_to_str(p['passphrase_hash'][-4:].encode('utf-8'))
        cache_file = os.path.join(dirname, "wallet_%s_cache.json" % (cf_id))
        p['cache_file'] = cache_file

        d = json.dumps(p).encode('utf-8')

        dirname = ""
        if isinstance(file_or_filename, str):
            dirname = os.path.dirname(file_or_filename)
            with open(file_or_filename, 'wb') as f:
                f.write(d)
            self._filename = file_or_filename
        else:
            # Assume it's file-like
            dirname = os.path.dirname(file_or_filename.name)
            file_or_filename.write(d)

        with open(cache_file, 'wb') as f:
            f.write(json.dumps(cache).encode('utf-8'))

    def sync_wallet_file(self):
        """ Syncs all wallet data to the wallet file used
            to construct this wallet instance, if one was used.
        """
        # TODO: In the future, we can keep track of whether syncing
        # is necessary and only write out if necessary.
        if self._filename:
            self.to_file(self._filename)
            self.logger.debug("Sync'ed file %s" % self._filename)

    def addresses(self, accounts=[]):
        """ Gets the address list for the current wallet.

        Args:
            accounts (list): A list of either account indices or names.

        Returns:
            dict: A dict keyed by account name containing a list of bitcoin
                addresses for that account.
        """
        addresses = {}
        for acct in self._check_and_get_accounts(accounts):
            addresses[acct.name] = acct.all_used_addresses

        return addresses

    @property
    def current_address(self):
        """ Gets the preferred address.

        Returns:
            str: The current preferred payment address.
        """
        return self.get_payout_address()

    def get_payout_address(self, account_name_or_index=None):
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

    def get_change_address(self, account_name_or_index=None):
        """ Gets the next change address.

        Args:
            account_name_or_index (str or int): The account to retrieve the
               change address from. If not provided, the default account (0')
               is used.

        Returns:
            str: A Base58Check encoded bitcoin address.
        """
        if account_name_or_index is None:
            acct = self._accounts[0]
        else:
            acct = self._check_and_get_accounts([account_name_or_index])[0]

        return acct.get_next_address(True)

    def get_payout_public_key(self, account_name_or_index=None):
        """ Gets the next payout public key.

        Args:
            account_name_or_index (str or int): The account to retrieve the
               payout address from. If not provided, the default account (0')
               is used.

        Returns:
            PublicKey: A public key object
        """
        if account_name_or_index is None:
            acct = self._accounts[0]
        else:
            acct = self._check_and_get_accounts([account_name_or_index])[0]

        return acct.get_next_public_key(False)

    def get_change_public_key(self, account_name_or_index=None):
        """ Gets the next change public_key.

        Args:
            account_name_or_index (str or int): The account to retrieve the
               change address from. If not provided, the default account (0')
               is used.

        Returns:
            PublicKey: A public key object
        """
        if account_name_or_index is None:
            acct = self._accounts[0]
        else:
            acct = self._check_and_get_accounts([account_name_or_index])[0]

        return acct.get_next_public_key(True)

    def sign_message(self, message,
                     account_name_or_index=None,
                     key_index=0):
        """ Signs an arbitrary message.

            This function signs the message using a specific key in a specific
            account. By default, if account or key are not given, it will
            use the first (default) account and the 0-th public key. In all
            circumstances it uses keys from the payout (external) chain.

        Note:
            This is different from `sign_bitcoin_message` as there is
            nothing prepended to the message and the signature
            recovery id is not provided, making public key recovery
            impossible.

        Args:
            message (bytes or str): Message to be signed.
            account_name_or_index (str or int): The account to retrieve the
               change address from. If not provided, the default account (0')
               is used.
            key_index (int): The index of the key in the external chain to use.

        Returns:
            str: A Base64-encoded string of the signature.
        """
        if account_name_or_index is None:
            acct = self._accounts[0]
        else:
            acct = self._check_and_get_accounts([account_name_or_index])[0]

        priv_key = acct.get_private_key(change=False, n=key_index)

        return base64.b64encode(bytes(priv_key.sign(message))).decode()

    def sign_bitcoin_message(self, message, address):
        """ Bitcoin signs an arbitrary message.

            This function signs the message using a specific key in a specific
            account. By default, if account or key are not given, it will
            use the first (default) account and the 0-th public key. In all
            circumstances it uses keys from the payout (external) chain.

        Note:
            b"\x18Bitcoin Signed Message:\n" + len(message) is prepended
            to the message before signing.

        Args:
            message (bytes or str): Message to be signed.
            address (str): Bitcoin address from which the private key will be
                retrieved and used to sign the message.

        Returns:
            str: A Base64-encoded string of the signature.
                The first byte of the encoded message contains information
                about how to recover the public key. In bitcoind parlance,
                this is the magic number containing the recovery ID and
                whether or not the key was compressed or not. (This function
                always processes full, uncompressed public-keys, so the magic
                number will always be either 27 or 28).
        """
        priv_key = self.get_private_key(address)

        if priv_key is None:
            raise ValueError("Address is not a part of this wallet.")

        return priv_key.sign_bitcoin(message, True).decode()

    def verify_bitcoin_message(self, message, signature, address):
        """ Verifies a bitcoin signed message

        Args:
            message(bytes or str): The message that the signature
                corresponds to.
            signature (bytes or str): A Base64 encoded signature
            address (str): Base58Check encoded address corresponding to the
                uncompressed key.

        Returns:
            bool: True if the signature verified properly, False otherwise.
        """
        if isinstance(message, str):
            msg = message.encode()
        else:
            msg = message

        return PublicKey.verify_bitcoin(message=msg,
                                        signature=signature,
                                        address=address)

    def get_message_signing_public_key(self,
                                       account_name_or_index=None,
                                       key_index=0):
        """ Retrieves the public key typically used for message
            signing. The default is to use the first account and
            the 0-th public key from the payout (external) chain.

        Args:
            account_name_or_index (str or int): The account to retrieve the
               public key from. If not provided, the default account (0')
               is used.
            key_index (int): The index of the key in the external chain to use.

        Returns:
            PublicKey: The public key object
        """
        if account_name_or_index is None:
            acct = self._accounts[0]
        else:
            acct = self._check_and_get_accounts([account_name_or_index])[0]

        # Return the PrivateKey object, not the HDPrivateKey object
        return acct.get_public_key(change=False, n=key_index)._key

    def broadcast_transaction(self, tx):
        """ Broadcasts the transaction to the Bitcoin network.

        Args:
            tx (str): Hex string serialization of the transaction to
               be broadcasted to the Bitcoin network..
        Returns:
            str: The name of the transaction that was broadcasted.
        """
        res = ""
        try:
            txid = self.data_provider.broadcast_transaction(tx)
            res = txid
        except exceptions.WalletError as e:
            self.logger.critical(
                "Problem sending transaction to network: %s" % e)

        return res

    def build_signed_transaction(self, addresses_and_amounts,
                                 use_unconfirmed=False, fees=None, accounts=[]):
        """ Makes raw signed unbroadcasted transaction(s) for the specified amount.

            In the future, this function may create multiple transactions
            if a single one would be too big.

        Args:
            addresses_and_amounts (dict): A dict keyed by recipient address
               and corresponding values being the amount - *in satoshis* - to
               send to that address.
            use_unconfirmed (bool): Use unconfirmed transactions if necessary.
            fees (int): Specify the fee amount manually.
            accounts (list(str or int)): List of accounts to use. If
               not provided, all discovered accounts may be used based
               on the chosen UTXO selection algorithm.

        Returns:
            list(Transaction): A list of Transaction objects
        """
        total_amount = sum([amt for amt in addresses_and_amounts.values()])

        if not accounts:
            accts = self._accounts
            c_balance = self.confirmed_balance()
            u_balance = self.unconfirmed_balance()
        else:
            accts = self._check_and_get_accounts(accounts)
            c_balance = 0
            u_balance = 0
            for a in accts:
                c_balance += a.balance['confirmed']
                u_balance += a.balance['total']

        if use_unconfirmed:
            balance = u_balance
        else:
            balance = min(c_balance, u_balance)

        # Now get the unspents from all accounts and select which we
        # want to use
        utxos_by_addr = self.get_utxos(accts)

        if not use_unconfirmed:
            # Filter out any UTXOs that are unconfirmed.
            for addr, utxos_addr in utxos_by_addr.items():
                utxos_by_addr[addr] = list(filter(lambda u: u.num_confirmations > 0,
                                                  utxos_addr))

        selected_utxos, fees = self.utxo_selector(data_provider=self.data_provider,
                                                  utxos_by_addr=utxos_by_addr,
                                                  amount=total_amount,
                                                  num_outputs=len(addresses_and_amounts),
                                                  fees=fees)

        # Verify we have enough money
        total_with_fees = total_amount + fees
        if total_with_fees > balance:
            raise exceptions.WalletBalanceError(
                "Balance (%d satoshis) is not sufficient to send %d satoshis + fees (%d satoshis)." %
                (balance, total_amount, fees))

        if not selected_utxos and not use_unconfirmed:
            raise exceptions.WalletBalanceError(
                "There are not enough confirmed UTXOs to complete this transaction.")

        if use_unconfirmed and total_with_fees > c_balance:
            self.logger.warning(
                "Using unconfirmed inputs to complete transaction.")

        # Get all private keys in one shot
        private_keys = self.get_private_keys(list(selected_utxos.keys()))

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
            addr_prefix, key_hash = utils.address_to_key_hash(addr)
            if addr_prefix in [0x05, 0xC4]:
                script = Script.build_p2sh(key_hash)
            else:
                script = Script.build_p2pkh(key_hash)
            outputs.append(TransactionOutput(value=amount,
                                             script=script))

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
                raise exceptions.WalletSigningError(
                    "Couldn't find address %s or unable to generate private key for it." % addr)

            for utxo in utxo_list:
                signed = txn.sign_input(input_index=i,
                                        hash_type=Transaction.SIG_HASH_ALL,
                                        private_key=private_key,
                                        sub_script=utxo.script)

                if not signed:
                    raise exceptions.WalletSigningError(
                        "Unable to sign input %d." % i)

                i += 1

        return [txn]

    def make_signed_transaction_for(self, address, amount,
                                    use_unconfirmed=False, fees=None,
                                    accounts=[]):
        """ Makes a raw signed unbroadcasted transaction for the specified amount.

        Args:
            address (str): The address to send the Bitcoin to.
            amount (number): The amount of Bitcoin to send.
            use_unconfirmed (bool): Use unconfirmed transactions if necessary.
            fees (int): Specify the fee amount manually.
            accounts (list(str or int)): List of accounts to use. If
               not provided, all discovered accounts may be used based
               on the chosen UTXO selection algorithm.

        Returns:
            list(dict): A list of dicts containing transaction names
               and raw transactions.  e.g.: [{"txid": txid0, "txn":
               txn_hex0}, ...]
        """
        return self.make_signed_transaction_for_multiple({address: amount},
                                                         use_unconfirmed=use_unconfirmed,
                                                         fees=fees,
                                                         accounts=accounts)

    def make_signed_transaction_for_multiple(self, addresses_and_amounts,
                                             use_unconfirmed=False, fees=None,
                                             accounts=[]):
        """ Makes raw signed unbroadcasted transaction(s) for the specified amount.

            In the future, this function may create multiple transactions
            if a single one would be too big.

        Args:
            addresses_and_amounts (dict): A dict keyed by recipient address
               and corresponding values being the amount - *in satoshis* - to
               send to that address.
            use_unconfirmed (bool): Use unconfirmed transactions if necessary.
            fees (int): Specify the fee amount manually.
            accounts (list(str or int)): List of accounts to use. If
               not provided, all discovered accounts may be used based
               on the chosen UTXO selection algorithm.

        Returns:
            list(dict): A list of dicts containing transaction names
               and raw transactions.  e.g.: [{"txid": txid0, "txn":
               txn_hex0}, ...]
        """

        txns = self.build_signed_transaction(addresses_and_amounts,
                                             use_unconfirmed=use_unconfirmed,
                                             fees=fees,
                                             accounts=accounts)
        return [{"txid": str(txn.hash), "txn": txn.to_hex()}
                for txn in txns]

    def send_to_multiple(self, addresses_and_amounts,
                         use_unconfirmed=False, fees=None, accounts=[]):
        """ Sends bitcoins to multiple addresses.

        Args:
            addresses_and_amounts (dict): A dict keyed by recipient address
               and corresponding values being the amount - *in satoshis* - to
               send to that address.
            use_unconfirmed (bool): Use unconfirmed transactions if necessary.
            fees (int): Specify the fee amount manually.
            accounts (list(str or int)): List of accounts to use. If
               not provided, all discovered accounts may be used based
               on the chosen UTXO selection algorithm.

        Returns:
            str or None: A string containing the submitted TXID or None.
        """
        txn_dict = self.make_signed_transaction_for_multiple(addresses_and_amounts,
                                                             use_unconfirmed,
                                                             fees,
                                                             accounts)

        res = []
        for t in txn_dict:
            txid = self.broadcast_transaction(t["txn"])
            if not txid:
                self.logger.critical("Unable to send txn %s" % t["txid"])
            elif txid != t["txid"]:
                # Something weird happened ...
                raise exceptions.TxidMismatchError("Transaction IDs do not match")
            else:
                res.append(t)

        return res

    def send_to(self, address, amount,
                use_unconfirmed=False, fees=None, accounts=[]):
        """ Sends Bitcoin to the provided address for the specified amount.

        Args:
            address (str): The address to send the Bitcoin too.
            amount (number): The amount of Bitcoin to send.
            use_unconfirmed (bool): Use unconfirmed transactions if necessary.
            fees (int): Specify the fee amount manually.
            accounts (list(str or int)): List of accounts to use. If
               not provided, all discovered accounts may be used based
               on the chosen UTXO selection algorithm.

        Returns:
            list(dict): A list of dicts containing transaction names
               and raw transactions.  e.g.: [{"txid": txid0, "txn":
               txn_hex0}, ...]
        """
        return self.send_to_multiple(addresses_and_amounts={address: amount},
                                     use_unconfirmed=use_unconfirmed,
                                     fees=fees,
                                     accounts=accounts)

    def get_utxos_above_threshold(self, threshold,
                                  include_unconfirmed=False, accounts=[]):
        """ Returns all UTXOs >= threshold satoshis.

        Args:
            threshold (int): UTXO value must be >= to this value.
            include_unconfirmed (bool): Include unconfirmed UTXOs.
            accounts (list(str or int)): List of accounts to use. If
                not provided, all discovered accounts will be done.
        """
        if not accounts:
            accts = self._accounts
        else:
            accts = self._check_and_get_accounts(accounts)

        utxos_by_addr = self.get_utxos(accts)
        num_conf = 0
        for addr, utxos_addr in utxos_by_addr.items():
            conf = list(filter(lambda u: u.num_confirmations > 0,
                               utxos_addr))

            num_conf += len(conf)

            if include_unconfirmed:
                conf = utxos_addr

            above_thresh = list(filter(lambda u: u.value >= threshold,
                                       conf))
            utxos_by_addr[addr] = above_thresh

        return utxos_by_addr, num_conf

    def _sum_utxos(self, utxos_by_addr):
        total_value = 0
        num_utxos = 0
        for addr, utxos in utxos_by_addr.items():
            num_utxos += len(utxos)
            total_value += sum([u.value for u in utxos])

        return total_value, num_utxos

    def sweep(self, address, accounts=[]):
        """ Sweeps the entire balance to a single address

        Args:
            address (str): Bitcoin address to send entire balance to.
            accounts (list(str or int)): List of accounts to use. If
                not provided, all discovered accounts will be done.

        Returns:
            list(str): List of txids used to complete the sweep.
        """
        if not accounts:
            accts = self._accounts
        else:
            accts = self._check_and_get_accounts(accounts)

        # Force address discovery
        for a in accts:
            a._discover_used_addresses(check_all=True)

        utxos_by_addr = self.get_utxos(accts)
        total_value, num_utxos = self._sum_utxos(utxos_by_addr)

        if total_value < self.DUST_LIMIT:
            raise exceptions.WalletBalanceError(
                "Total balance (%d satoshis) is less than the dust limit. Not sweeping." %
                (total_value))

        # Compute an approximate fee
        fees = num_utxos * DEFAULT_INPUT_FEE + DEFAULT_OUTPUT_FEE

        curr_utxo_selector = self.utxo_selector
        s = lambda data_provider, utxos_by_addr, amount, num_outputs, fees: (utxos_by_addr, fees)

        self.utxo_selector = s
        tx_list = self.send_to(address=address,
                               amount=total_value - fees,
                               use_unconfirmed=True,
                               fees=fees,
                               accounts=accts)

        self.utxo_selector = curr_utxo_selector

        return [t['txid'] for t in tx_list]

    def spread_utxos(self, threshold, num_addresses, accounts=[]):
        """ Spreads out UTXOs >= threshold satoshis to a set
            of new change addresses.

        Args:
            threshold (int): UTXO value must be >= to this value.
            num_addresses (int): Number of addresses to spread out the
                matching UTXOs over. This must be > 1 and <= 100.
            accounts (list(str or int)): List of accounts to use. If
                not provided, all discovered accounts will be done.
        """
        # Limit the number of spreading addresses so that we don't
        # create unnecessarily large transactions
        if num_addresses < 1 or num_addresses > 100:
            raise ValueError("num_addresses must be > 0 and <= 100.")

        if not accounts:
            accts = self._accounts
        else:
            accts = self._check_and_get_accounts(accounts)

        txids = []
        for acct in accts:
            utxos_by_addr, num_conf = self.get_utxos_above_threshold(threshold,
                                                                     False,
                                                                     [acct])
            # Total up the value
            total_value, num_utxos = self._sum_utxos(utxos_by_addr)

            if num_utxos == 0:
                self.logger.error("No matching UTXOs for account %s (%d confirmed UTXOs). Not spreading." %
                                  (acct.name, num_conf))
                break

            # Get the next num_addresses change addresses
            # We force address discovery here to make sure change
            # address generation doesn't end up violating the GAP
            # limit
            acct._discover_used_addresses(check_all=True)
            change_addresses = [acct.get_address(True)
                                for i in range(num_addresses)]

            # Compute an approximate fee
            fees = num_utxos * DEFAULT_INPUT_FEE + \
                   num_addresses * DEFAULT_OUTPUT_FEE

            spread_amount = total_value - fees
            per_addr_amount = int(spread_amount / num_addresses)
            if per_addr_amount <= self.DUST_LIMIT:
                self.logger.error(
                    "Amount to each address (%d satoshis) would be less than the dust limit. Choose a smaller number of addresses." %
                    per_addr_amount)
                break

            curr_utxo_selector = self.utxo_selector
            s = lambda data_provider, utxos_by_addr, amount, num_outputs, fees: (utxos_by_addr, fees)

            self.utxo_selector = s

            addresses_and_amounts = {}
            for c in change_addresses:
                addresses_and_amounts[c] = per_addr_amount

            txids += self.send_to_multiple(addresses_and_amounts=addresses_and_amounts,
                                           use_unconfirmed=False,
                                           fees=fees,
                                           accounts=[acct])


            self.utxo_selector = curr_utxo_selector

        return txids

    @property
    def balances(self):
        """ Balance for the wallet.

        Returns:
            dict: keys are 'confirmed' and 'total' with values being in
                satoshis. The 'total' balance includes any unconfirmed
                transactions.
        """
        balances = {'confirmed': 0, 'total': 0}
        for acct in self._accounts:
            acct_balance = acct.balance
            balances['confirmed'] += acct_balance['confirmed']
            balances['total'] += acct_balance['total']

        return balances

    def confirmed_balance(self, account_name_or_index=None):
        """ Gets the current confirmed balance of the wallet in Satoshi.

        Args:
            account_name_or_index (str or int): The account to retrieve the
               payout address from. If not provided, the default account (0')
               is used.

        Returns:
            number: The current confirmed balance.
        """
        rv = None
        if account_name_or_index is None:
            rv = self.balances['confirmed']
        else:
            acct = self._check_and_get_accounts([account_name_or_index])[0]
            rv = acct.balance['confirmed']

        return rv

    def unconfirmed_balance(self, account_name_or_index=None):
        """ Gets the current total balance of the wallet in Satoshi,
            including unconfirmed transactions

        Args:
            account_name_or_index (str or int): The account to retrieve the
               payout address from. If not provided, the default account (0')
               is used.

        Returns:
            number: The current unconfirmed balance.
        """
        rv = None
        if account_name_or_index is None:
            rv = self.balances['total']
        else:
            acct = self._check_and_get_accounts([account_name_or_index])[0]
            rv = acct.balance['total']

        return rv

    @property
    def accounts(self):
        """ All accounts in the wallet.

        Returns:
            list(HDAccount): List of HDAccount objects.
        """
        return self._accounts

    @property
    def account_names(self):
        """ Names of all accounts in the wallet.

        Returns:
            list(str): All account names.
        """
        return list(self._account_map.keys())


class Two1WalletProxy(object):
    """ Abstraction layer between wallet object and wallet daemon proxy.

        This class implements abstracts away between usage of a wallet
        object when a daemon is not found/running and a daemon proxy object
        when a daemon is running.

    Args:
        wallet_path (str): Path to the wallet to be opened.
        data_provider (BaseProvider): A blockchain data provider object.
        passphrase (str): Passphrase used to unlock the wallet, if necessary.

    Returns:
        Two1WalletProxy: A proxy object.
    """

    @staticmethod
    def check_daemon_running(wallet_path=Two1Wallet.DEFAULT_WALLET_PATH):
        """ Checks whether the wallet daemon is running.

        Args:
            wallet_path (str): The path to the wallet that the daemon
                should have loaded up.

        Returns:
            UnixSocketServerProxy: Returns the wallet proxy object
                used to communicate with the daemon, or None if the
                daemon is not running.
        """
        rv = None
        try:
            w = UnixSocketServerProxy()

            # Check the path to make sure it's the same
            wp = w.wallet_path()
            rv = w if wp == wallet_path else None

        except (exceptions.DaemonNotRunningError, ReceivedErrorResponse) as e:
            rv = None

        return rv

    @staticmethod
    def check_wallet_proxy_unlocked(w, passphrase):
        """ Checks if the wallet currently loaded by the daemon
            is unlocked.

        Args:
            w (UnixSocketServerProxy): The wallet proxy object to check.
            passphrase (str): The passphrase to send if the wallet is
                locked.
        """
        if w.is_locked():
            if not passphrase:
                print("The wallet is locked and requires a passphrase.")
                passphrase = getpass.getpass("Passphrase to unlock wallet: ")

            w.unlock(passphrase)

        return not w.is_locked()

    def __init__(self, wallet_path, data_provider=None, passphrase=''):
        w = Two1WalletProxy.check_daemon_running(wallet_path)
        if w is not None:
            self.w = w
            Two1WalletProxy.check_wallet_proxy_unlocked(w, passphrase)
        else:
            if data_provider is None:
                dp = TwentyOneProvider()
            else:
                dp = data_provider
            self.w = Two1Wallet(params_or_file=wallet_path,
                                data_provider=dp,
                                passphrase=passphrase)

    def get_private_for_public(self, public_key):
        rv = None
        if isinstance(self.w, Two1Wallet):
            rv = self.w.get_private_for_public(public_key)
        else:
            if isinstance(public_key, HDPublicKey):
                pub_key = public_key.to_b58check()
            else:
                pub_key = public_key.to_base64().decode()
            rv = self.w.get_private_for_public(pub_key)
            if rv is not None:
                rv = HDPrivateKey.from_b58check(rv)

        return rv

    def get_change_public_key(self, account=None):
        rv = self.w.get_change_public_key(account)
        if not isinstance(self.w, Two1Wallet):
            rv = HDPublicKey.from_b58check(rv)

        return rv

    def get_payout_public_key(self, account=None):
        rv = self.w.get_payout_public_key(account)
        if not isinstance(self.w, Two1Wallet):
            rv = HDPublicKey.from_b58check(rv)

        return rv

    def get_message_signing_public_key(self,
                                       account_name_or_index=None,
                                       key_index=0):
        rv = self.w.get_message_signing_public_key(account_name_or_index,
                                                   key_index)
        if not isinstance(self.w, Two1Wallet):
            rv = PublicKey.from_base64(rv)

        return rv

    def build_signed_transaction(self, addresses_and_amounts,
                                 use_unconfirmed=False,
                                 fees=None, accounts=[]):

        rv = self.w.build_signed_transaction(addresses_and_amounts,
                                             use_unconfirmed,
                                             fees,
                                             accounts)
        if not isinstance(self.w, Two1Wallet):
            rv = [Transaction.from_hex(t) for t in rv]

        return rv

    def exception_info(self):
        if not isinstance(self.w, Two1Wallet):
            return self.w.exception_info()
        else:
            return dict(message="Fix me")

    def __getattr__(self, method_name):
        rv = None
        if hasattr(self.w, method_name):
            attr = getattr(self.w, method_name)

            def wrapper(*args, **kwargs):
                return attr(*args, **kwargs)

            if isinstance(self.w, Two1Wallet):
                # If it's the actual wallet object, just return the
                # attribute
                rv = attr
            else:
                # If it's the proxy object we need to be a bit more
                # creative: we should look up whether this is a
                # property and if it is actually call the function.
                if isinstance(getattr(Two1Wallet, method_name), property):
                    rv = attr()
                else:
                    rv = wrapper
        else:
            raise exceptions.UndefinedMethodError(
                "wallet has no method or property: %s" % (method_name))

        return rv
