import base64
import json
import os

import pyaes
from pbkdf2 import PBKDF2

from two1.bitcoin.crypto import HDKey
from two1.bitcoin.crypto import HDPrivateKey
from two1.bitcoin.script import Script
from two1.bitcoin.txn import Transaction
from two1.bitcoin.txn import TransactionInput
from two1.bitcoin.txn import TransactionOutput
from two1.bitcoin import utils
from two1.blockchain.chain_provider import ChainProvider
from two1.wallet import exceptions
from two1.wallet.account_types import account_types
from two1.wallet.hd_account import HDAccount
from two1.wallet.base_wallet import BaseWallet
from two1.wallet.utxo_selectors import utxo_selector_smallest_first


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
    DUST_LIMIT = 5460  # Satoshis - should this be somewhere else?
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
                      "data_provider": ['chain'],
                      "data_provider_params": {},
                      "testnet": [True, False],
                      "wallet_path": ""}

    required_params = ['master_key', 'locked', 'key_salt', 'passphrase_hash',
                       'account_type']

    @staticmethod
    def is_configured():
        """ Returns the configuration/initialization status of the
            wallet.

        Returns:
            bool: True if the default wallet has been configured and
                ready to use otherwise False
        """
        if os.path.exists(Two1Wallet.DEFAULT_WALLET_PATH):
            # Check if the config is actually good
            params = {}
            with open(Two1Wallet.DEFAULT_WALLET_PATH, 'r') as f:
                params = json.load(f)

            for rp in Two1Wallet.required_params:
                if rp not in params:
                    return False

            return True
        else:
            return False

    @staticmethod
    def configure(config_options):
        """ Creates a default wallet.

            If 'wallet_path' is found in config_options, the wallet is
            stored at that location. Otherwise, it is created in
            ~/.two1/wallet/default_wallet.json.

        Args:
            config_options (dict): A dict of config options, the keys
                and allowed values of each key are found in the class
                variable of the same name. When 'chain' is specified as
                the value for 'data_provider', a second key
                'data_provider_params' must be supplied with a dict
                containing the 'api_key_id' and 'api_key_secret'.

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
                print("File %s already present. Not creating wallet." %
                      wallet_path)
                return False

        dp = Two1Wallet.instantiate_data_provider(data_provider_name=config_options['data_provider'],
                                                  data_provider_params=config_options['data_provider_params'])

        passphrase = config_options.get("passphrase", "")
        testnet = config_options.get("testnet", False)
        wallet = Two1Wallet.create(data_provider=dp,
                                   passphrase=passphrase,
                                   account_type=config_options['account_type'],
                                   testnet=testnet)

        wallet.discover_accounts()
        wallet.to_file(wallet_path)

        return os.path.exists(wallet_path)

    @staticmethod
    def instantiate_data_provider(data_provider_name, data_provider_params):
        # Create the default txn data provider
        if data_provider_name == 'chain':
            return ChainProvider(api_key_id=data_provider_params['chain_api_key_id'],
                                 api_key_secret=data_provider_params['chain_api_key_secret'])
        else:
            raise exceptions.UnknownDataProviderError()

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
        account_type = "BIP44Testnet" if testnet else Two1Wallet.DEFAULT_ACCOUNT_TYPE
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

        adder = " (and your passphrase) " if passphrase else " "
        print("Your wallet can be recovered using the following set of words (in that order).")
        print("Please store them%ssafely." % adder)
        print("\n%s\n" % mnemonic)

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
        self._testnet = self.account_type == 'BIP44Testnet'

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
            tx (str): Hex string serialization of the transaction to
               be broadcasted to the Bitcoin network..
        Returns:
            str: The name of the transaction that was broadcasted.
        """
        res = ""
        try:
            txid = self.data_provider.send_transaction(tx)
            res = txid
        except exceptions.WalletError as e:
            print("Problem sending transaction to network: %s" % e)

        return res

    def make_signed_transaction_for(self, address, amount, accounts=[]):
        """ Makes a raw signed unbroadcasted transaction for the specified amount.

        Args:
            address (str): The address to send the Bitcoin to.
            amount (number): The amount of Bitcoin to send.
            accounts (list(str or int)): List of accounts to use. If
               not provided, all discovered accounts may be used based
               on the chosen UTXO selection algorithm.

        Returns:
            list(dict): A list of dicts containing transaction names
               and raw transactions.  e.g.: [{"txid": txid0, "txn":
               txn_hex0}, ...]
        """
        return self.make_signed_transaction_for_multiple({address: amount},
                                                         accounts)

    def make_signed_transaction_for_multiple(self, addresses_and_amounts,
                                             accounts=[]):
        """ Makes raw signed unbrodcasted transaction(s) for the specified amount.

            In the future, this function may create multiple transactions
            if a single one would be too big.

        Args:
            addresses_and_amounts (dict): A dict keyed by recipient address
               and corresponding values being the amount - *in satoshis* - to
               send to that address.
            accounts (list(str or int)): List of accounts to use. If
               not provided, all discovered accounts may be used based
               on the chosen UTXO selection algorithm.

        Returns:
            list(dict): A list of dicts containing transaction names
               and raw transactions.  e.g.: [{"txid": txid0, "txn":
               txn_hex0}, ...]
        """
        total_amount = sum([amt for amt in addresses_and_amounts.values()])

        if not accounts:
            accts = self._accounts
        else:
            accts = self._check_and_get_accounts(accounts)

        # Now get the unspents from all accounts and select which we
        # want to use
        utxos_by_addr = self.get_utxos(accts)

        selected_utxos, fees = self.utxo_selector(data_provider=self.data_provider,
                                                  utxos_by_addr=utxos_by_addr,
                                                  amount=total_amount,
                                                  num_outputs=len(addresses_and_amounts))

        total_with_fees = total_amount + fees

        # Verify we have enough money
        # First element is confirmed balance
        if total_with_fees > self.confirmed_balance():
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

        return [{"txid": str(txn.hash), "txn": utils.bytes_to_str(bytes(txn))}]

    def send_to_multiple(self, addresses_and_amounts, accounts=[]):
        """ Sends bitcoins to multiple addresses.

        Args:
            addresses_and_amounts (dict): A dict keyed by recipient address
               and corresponding values being the amount - *in satoshis* - to
               send to that address.
            accounts (list(str or int)): List of accounts to use. If
               not provided, all discovered accounts may be used based
               on the chosen UTXO selection algorithm.

        Returns:
            str or None: A string containing the submitted TXID or None.
        """
        txn_dict = self.make_signed_transaction_for_multiple(addresses_and_amounts,
                                                             accounts)

        res = []
        for t in txn_dict:
            txid = self.broadcast_transaction(t["txn"])
            if not txid:
                print("Unable to send txn %s" % t["txid"])
            elif txid != t["txid"]:
                # Something weird happened ...
                raise exceptions.TxidMismatchError("Transaction IDs do not match")
            else:
                res.append(t)

        return res

    def send_to(self, address, amount, accounts=[]):
        """ Sends Bitcoin to the provided address for the specified amount.

        Args:
            address (str): The address to send the Bitcoin too.
            amount (number): The amount of Bitcoin to send.
            accounts (list(str or int)): List of accounts to use. If
               not provided, all discovered accounts may be used based
               on the chosen UTXO selection algorithm.

        Returns:
            list(dict): A list of dicts containing transaction names
               and raw transactions.  e.g.: [{"txid": txid0, "txn":
               txn_hex0}, ...]
        """
        return self.send_to_multiple({address: amount}, accounts)

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

    def confirmed_balance(self):
        """ Gets the current confirmed balance of the wallet in Satoshi.

        Returns:
            number: The current confirmed balance.
        """
        return self.balances['confirmed']

    def unconfirmed_balance(self):
        """ Gets the current total balance of the wallet in Satoshi,
            including unconfirmed transactions

        Returns:
            number: The current unconfirmed balance.
        """
        return self.balances['total']

    @property
    def accounts(self):
        """ All accounts in the wallet.

        Returns:
            list(HDAccount): List of HDAccount objects.
        """
        return self._accounts
