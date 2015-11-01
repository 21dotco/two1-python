import logging
import logging.handlers
import signal
import sys
import threading
import time

import click
import json
from jsonrpcserver import Methods
from jsonrpcserver.exceptions import ServerError
from path import Path
from two1.lib.bitcoin.crypto import PublicKey
from two1.lib.bitcoin.crypto import HDPublicKey
from two1.lib.wallet.socket_rpc_server import UnixSocketJSONRPCServer
from two1.lib.wallet.exceptions import AccountCreationError
from two1.lib.wallet.exceptions import DaemonRunningError
from two1.lib.wallet.exceptions import WalletBalanceError
from two1.lib.wallet.exceptions import WalletLockedError
from two1.lib.wallet.exceptions import WalletNotLoadedError
from two1.lib.wallet.two1_wallet import Two1Wallet
from two1.lib.wallet.cli import validate_data_provider
from two1.lib.wallet.cli import WALLET_VERSION

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
DEF_WALLET_UPDATE_INTERVAL = 25   # seconds
MAX_WALLET_UPDATE_INTERVAL = 300  # seconds

logger = logging.getLogger('walletd')
methods = Methods()
wallet = dict(obj=None,
              locked=False,
              path=None,
              data_provider=None,
              update_info=dict(interval=DEF_WALLET_UPDATE_INTERVAL,
                               last_update=time.time(),
                               last_connection=time.time(),
                               in_need=False))
wallet_dict_lock = threading.Lock()
client_lock = threading.Lock()


def track_connections_cb(data):
    """ Keep track of connection times to dynamically
        update the update interval. This gets called by
        the RPC server thread as a callback.
    """
    now = time.time()
    since_last = now - wallet['update_info']['last_update']
    wallet['update_info']['last_connection'] = now

    if since_last > DEF_WALLET_UPDATE_INTERVAL:
        if wallet_dict_lock.acquire(True, 0.01):
            wallet['update_info']['in_need'] = True
            wallet_dict_lock.release()

    curr_interval = wallet['update_info']['interval']
    if curr_interval > DEF_WALLET_UPDATE_INTERVAL:
        if wallet_dict_lock.acquire(True, 0.01):
            logger.info("Resetting update interval to %ds" %
                        DEF_WALLET_UPDATE_INTERVAL)
            wallet['update_info']['interval'] = DEF_WALLET_UPDATE_INTERVAL
        wallet_dict_lock.release()


def sig_handler(sig_num, stack_frame):
    """ Signal handler to shut down upon received signals.

        Upon receiving any signal, this function initiates
        a complete daemon shutdown.

    Args:
        signum (int): The signal number that was sent.
        stack_frame (str): Current stack frame.
    """
    logger.info("Shutting down...")
    rpc_server.shutdown()


def _handle_exception(e):
    logger.debug("exception: %s" % str(e))
    data = dict(type=e.__class__.__name__,
                message=str(e))
    raise ServerError(data=json.dumps(data))


def do_update(block_on_acquire=True):
    """ Updates the wallet info.
    """
    if wallet['obj']:
        lock_acquired = False
        try:
            if wallet_dict_lock.acquire(block_on_acquire):
                lock_acquired = True
                logger.debug("Starting wallet update ...")
                wallet['obj']._sync_accounts()
                wallet['update_info']['last_update'] = time.time()
                logger.debug("Completed update.")

                if wallet['update_info']['in_need']:
                    wallet['update_info']['in_need'] = False

        except Exception as e:
            logger.error("Couldn't update balances: %s" % e)
        finally:

            # Check if we should update the interval
            curr_interval = wallet['update_info']['interval']
            since_last_conn = int(
                time.time() - wallet['update_info']['last_connection'])
            if since_last_conn > curr_interval and \
               curr_interval < MAX_WALLET_UPDATE_INTERVAL:
                new_interval = 2 * curr_interval
                # Clamp to max
                if new_interval > MAX_WALLET_UPDATE_INTERVAL:
                    new_interval = MAX_WALLET_UPDATE_INTERVAL
                wallet['update_info']['interval'] = new_interval
                logger.info("No connections in %ds. Setting interval to %ds." %
                            (since_last_conn,
                             new_interval))
            if lock_acquired:
                wallet_dict_lock.release()


def data_updater():
    """ Update thread target.

        This function updates the account balances based on the
        interval (default of 25 secons).
    """
    # This is a daemon thread so no need to explicitly
    # poll for any shutdown events.
    sleep_time = 0
    while True:
        interval = wallet['update_info']['interval']
        if time.time() > sleep_time + interval or \
           wallet['update_info']['in_need']:
            do_update()
            sleep_time = time.time()
        time.sleep(1)


def load_wallet(wallet_path, data_provider, passphrase):
    """ Loads a wallet.

    Args:
        wallet_path (str): The path to the wallet to be loaded.
        data_provider (BaseProvider): A blockchain data provider object.
        passphrase (str): Passphrase to use to unlock the wallet if the
            wallet requires unlocking.
    """
    global wallet

    try:
        logger.debug("In load_wallet...")
        logger.debug("\twallet_path = %s" % wallet_path)
        logger.debug("\tdata_provider = %r" % data_provider)
        logger.debug("\tpassphrase = %r" % bool(passphrase))
        wallet['obj'] = Two1Wallet(params_or_file=wallet_path,
                                   data_provider=data_provider,
                                   passphrase=passphrase)
        wallet['locked'] = False
    except Exception as e:
        raise WalletNotLoadedError("Wallet loading failed: %s" % e)


def _check_wallet_loaded():
    """ Raises an error if the wallet is locked or not loaded.
    """
    logger.debug("wallet obj = %r, wallet locked = %r" % (wallet['obj'],
                                                          wallet['locked']))
    if wallet['obj'] is None and not wallet['locked']:
        # Try loading
        try:
            load_wallet(wallet_path=wallet['path'],
                        data_provider=wallet['data_provider'],
                        passphrase="")
        except WalletNotLoadedError as e:
            _handle_exception(e)

    if wallet['locked']:
        _handle_exception(WalletLockedError(
            "Wallet is locked. Use the 'unlock' command with the passphrase as an arg."))


def daemon_method(f):
    """ Decorator function to create a daemon method.

        This function also checks if the wallet is loaded and handles
        exceptions.

    Args:
        f (function): The function to make a daemon method

    Returns:
        function: A wrapper function
    """
    def wrapper(params):
        _check_wallet_loaded()
        logger.debug("%s(%r, %r)" % (f.__name__,
                                     params['args'],
                                     params['kwargs']))
        try:
            return f(*params['args'], **params['kwargs'])
        except Exception as e:
            _handle_exception(e)

    methods.add(wrapper, f.__name__)

    return wrapper


@daemon_method
def testnet():
    """ RPC method to determine whether the wallet is a testnet wallet.

    Returns:
        bool: True if the wallet is a testnet wallet, False otherwise.
    """
    return wallet['obj'].testnet


@daemon_method
def confirmed_balance(account=None):
    """ RPC method to get the current confirmed balance.

    Returns:
        int: Current confirmed balance in satoshis.
    """
    return wallet['obj'].confirmed_balance(account)


@daemon_method
def unconfirmed_balance(account=None):
    """ RPC method to get the current unconfirmed balance.

    Returns:
        int: Current unconfirmed balance in satoshis.
    """
    return wallet['obj'].unconfirmed_balance(account)


@daemon_method
def get_private_for_public(public_key):
    """ RPC method to get the private key for the given public_key, if it is
        a part of this wallet.

    Args:
        public_key (str): Base58Check encoded serialization of the public key.

    Returns:
        str: A Base58Check encoded serialization of the private key object
           or None.
    """
    w = wallet['obj']
    try:
        pub_key = HDPublicKey.from_b58check(public_key)
    except ValueError:
        pub_key = PublicKey.from_base64(public_key)
    priv_key = w.get_private_key(pub_key.address(testnet=w._testnet))

    return priv_key.to_b58check() if priv_key is not None else None


@daemon_method
def current_address():
    """ RPC method to get the current payout address.

    Returns:
        str: Base58Check encoded bitcoin address.
    """
    return wallet['obj'].current_address


@daemon_method
def get_change_address(account=None):
    """ RPC method to get the current change address.

    Returns:
        str: Base58Check encoded bitcoin address.
    """
    return wallet['obj'].get_change_address(account)


@daemon_method
def get_payout_address(account=None):
    """ RPC method to get the current payout address.

        This is an alias for current_address but allows
        passing in an account
    Returns:
        str: Base58Check encoded bitcoin address.
    """
    return wallet['obj'].get_payout_address(account)


@daemon_method
def get_change_public_key(account=None):
    """ RPC method to get the current change public key.

    Returns:
        str: A Base58Check encoded serialization of the public key
    """
    return wallet['obj'].get_change_public_key(account).to_b58check()


@daemon_method
def get_payout_public_key(account=None):
    """ RPC method to get the current payout public key.

    Returns:
        str: A Base58Check encoded serialization of the public key
    """
    return wallet['obj'].get_payout_public_key(account).to_b58check()


@daemon_method
def sign_message(message,
                 account_name_or_index=None,
                 key_index=0):
    """ RPC method to sign an arbitrary message

    Args:
        message (bytes or str): Message to be signed.
        account_name_or_index (str or int): The account to retrieve the
           change address from. If not provided, the default account (0')
           is used.
        key_index (int): The index of the key in the external chain to use.

    Returns:
        str: A Base64-encoded string containing the signature.
    """
    return wallet['obj'].sign_message(message,
                                      account_name_or_index,
                                      key_index)


@daemon_method
def sign_bitcoin_message(message, address):
    """ RPC method to bitcoin sign an arbitrary message

    Args:
        message (bytes or str): Message to be signed.
        address (str): Bitcoin address from which the private key will be
            retrieved and used to sign the message.

    Returns:
        str: A Base64-encoded string containing the signature with recovery id
            embedded.
    """
    return wallet['obj'].sign_bitcoin_message(message, address)


@daemon_method
def verify_bitcoin_message(message, signature, address):
    """ RPC method to verify a bitcoin signed message

    Args:
        message(bytes or str): The message that the signature corresponds to.
        signature (bytes or str): A Base64 encoded signature
        address (str): Base58Check encoded address corresponding to the
           uncompressed key.

    Returns:
        bool: True if the signature verified properly, False otherwise.
    """
    return wallet['obj'].verify_bitcoin_message(message,
                                                signature,
                                                address)


@daemon_method
def get_message_signing_public_key(account_name_or_index=None,
                                   key_index=0):
    """ RPC method to get the public key used for message signing.

    Args:
        account_name_or_index (str or int): The account to retrieve the
            public key from. If not provided, the default account (0')
            is used.
        key_index (int): The index of the key in the external chain to use.

    Returns:
        str: Base64 representation of the public key
    """
    pub_key = wallet['obj'].get_message_signing_public_key(account_name_or_index,
                                                           key_index)
    return pub_key.to_base64().decode()


@daemon_method
def build_signed_transaction(addresses_and_amounts, use_unconfirmed=False,
                             insert_into_cache=False, fees=None, accounts=[]):
    """ RPC method to build and sign a transaction.

    Args:
        addresses_and_amounts (dict): A dict keyed by recipient address
           and corresponding values being the amount - *in satoshis* - to
           send to that address.
        use_unconfirmed (bool): Use unconfirmed transactions if necessary.
        insert_into_cache (bool): Insert the transaction into the
           wallet's cache and mark it as provisional.
        fees (int): Specify the fee amount manually.
        accounts (list(str or int)): List of accounts to use. If
           not provided, all discovered accounts may be used based
           on the chosen UTXO selection algorithm.

    Returns:
        list(WalletTransaction): A list of WalletTransaction objects
    """
    txns = wallet['obj'].build_signed_transaction(addresses_and_amounts,
                                                  use_unconfirmed,
                                                  insert_into_cache,
                                                  fees,
                                                  accounts)
    txns_ser = [t._serialize() for t in txns]
    logger.debug("txns: %r" % (txns_ser))
    return txns_ser


@daemon_method
def make_signed_transaction_for(address, amount,
                                use_unconfirmed=False,
                                insert_into_cache=False,
                                fees=None,
                                accounts=[]):
    """ Makes a raw signed unbroadcasted transaction for the specified amount.

    Args:
        address (str): The address to send the Bitcoin to.
        amount (number): The amount of Bitcoin to send.
        use_unconfirmed (bool): Use unconfirmed transactions if necessary.
        insert_into_cache (bool): Insert the transaction into the
           wallet's cache and mark it as provisional.
        fees (int): Specify the fee amount manually.
        accounts (list(str or int)): List of accounts to use. If
           not provided, all discovered accounts may be used based
           on the chosen UTXO selection algorithm.

    Returns:
        list(dict): A list of dicts containing transaction names
           and raw transactions.  e.g.: [{"txid": txid0, "txn":
           txn_hex0}, ...]
    """
    w = wallet['obj']
    txns = w.make_signed_transaction_for(address, amount,
                                         use_unconfirmed,
                                         insert_into_cache,
                                         fees,
                                         accounts)
    logger.debug("txns: %r" % ([t['txid'] for t in txns]))
    txns_ser = [dict(txid=t["txid"],
                     txn=t["txn"]._serialize()) for t in txns]

    return txns_ser


@daemon_method
def send_to(address, amount,
            use_unconfirmed=False, fees=None,
            accounts=[]):
    """ RPC method to send BTC to an address.

    Args:
        address (str): Base58Check encoded bitcoin address to send coins to.
        amount (int): Amount in satoshis to send.
        use_unconfirmed (bool): Use unconfirmed UTXOs if True.
        fees (int): User-specified fee amount
        accounts (list): List of accounts to use in sending coins.

    Returns:
        list: List of txids used to send the coins.
    """
    txns = wallet['obj'].send_to(address=address,
                                 amount=amount,
                                 use_unconfirmed=use_unconfirmed,
                                 fees=fees,
                                 accounts=accounts)
    logger.debug("txns: %r" % ([t['txid'] for t in txns]))
    txns_ser = [dict(txid=t["txid"],
                     txn=t["txn"]._serialize()) for t in txns]

    return txns_ser


@methods.add
def unlock(passphrase):
    """ RPC method to unlock wallet.

    Args:
        passphrase (str): The passphrase to use to unlock the wallet.
    """
    global wallet
    if not wallet['locked']:
        _handle_exception("Wallet is already unlocked or does not use a passphrase.")

    logger.info("Wallet unlocked. Loading ...")
    load_wallet(wallet_path=wallet['path'],
                data_provider=wallet['data_provider'],
                passphrase=passphrase)
    logger.info("... loading complete.")


@daemon_method
def is_locked():
    """ RPC method to determine whether the wallet is currently locked.

    Returns:
        bool: True if the wallet is locked, False if not.
    """
    return wallet['locked']


@daemon_method
def wallet_path():
    """ RPC method to return the wallet path of the currently loaded wallet.

    Returns:
        str: The path to the currently loaded wallet.
    """
    return wallet['path']


@daemon_method
def sync_wallet_file():
    """ RPC method to trigger a write to the wallet file.
    """
    return wallet['obj'].sync_wallet_file()


@daemon_method
def create_account(name):
    """ RPC method to create an account
    """
    return wallet['obj'].create_account(name)


@daemon_method
def account_names():
    """ RPC method to return all account names
    """
    return wallet['obj'].account_names


@daemon_method
def account_map():
    """ RPC method to return the account map
    """
    return wallet['obj'].account_map


@daemon_method
def addresses(accounts):
    """ RPC method to return all addresses
    """
    return wallet['obj'].addresses(accounts)


@daemon_method
def balances_by_address(account):
    """ RPC method to return balances by address
    """
    return wallet['obj'].balances_by_address(account)

@daemon_method
def sweep(address, accounts=[]):
    """ RPC method to sweep balance to a single address
    """
    return wallet['obj'].sweep(address, accounts)


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--wallet-path', '-wp',
              default=Two1Wallet.DEFAULT_WALLET_PATH,
              type=click.Path(exists=True, resolve_path=True),
              show_default=True,
              help='Path to wallet file')
@click.option('--blockchain-data-provider', '-b',
              default='twentyone',
              type=click.Choice(['twentyone', 'chain']),
              show_default=True,
              callback=validate_data_provider,
              help='Blockchain data provider service to use')
@click.option('--chain-api-key-id', '-ck',
              metavar='STRING',
              envvar='CHAIN_API_KEY_ID',
              is_eager=True,
              help='Chain API Key (only if -b chain)')
@click.option('--chain-api-key-secret', '-cs',
              metavar='STRING',
              envvar='CHAIN_API_KEY_SECRET',
              is_eager=True,
              help='Chain API Secret (only if -b chain)')
@click.option('--data-update-interval', '-u',
              type=click.IntRange(min=10, max=30),
              default=DEF_WALLET_UPDATE_INTERVAL,
              show_default=True,
              help='How often to update wallet data (seconds)')
@click.option('--debug', '-d',
              is_flag=True,
              help='Sets the logging level to debug')
@click.version_option(WALLET_VERSION)
@click.pass_context
def main(ctx, wallet_path, blockchain_data_provider,
         chain_api_key_id, chain_api_key_secret, data_update_interval,
         debug):
    """ Two1 Wallet daemon
    """
    global DEF_WALLET_UPDATE_INTERVAL

    wp = Path(wallet_path)
    # Initialize some logging handlers
    ch = logging.handlers.TimedRotatingFileHandler(wp.dirname().joinpath("walletd.log"),
                                                   when='midnight',
                                                   backupCount=5)
    ch_formatter = logging.Formatter(
        '%(asctime)s %(levelname)s %(name)-8s: %(message)s')
    ch.setFormatter(ch_formatter)
    ch.setLevel(logging.DEBUG if debug else logging.INFO)
    logging.getLogger().addHandler(ch)

    console = logging.StreamHandler()
    console.setLevel(logging.CRITICAL)
    logging.getLogger().addHandler(console)

    logging.getLogger().setLevel(logging.DEBUG)

    global wallet

    wallet['path'] = wallet_path
    if not Two1Wallet.check_wallet_file(wallet['path']):
        logger.critical("Wallet file does not exist or have the right parameters.")
        sys.exit(-1)

    wallet['data_provider'] = ctx.obj['data_provider']
    if data_update_interval is not None:
        DEF_WALLET_UPDATE_INTERVAL = data_update_interval
        wallet['update_info']['interval'] = data_update_interval

    logger.info("Starting daemon for wallet %s" % wallet_path)
    logger.info("Blockchain data provider: %s" %
                ctx.obj['data_provider'].__class__.__name__)
    logger.info("Update interval: %ds" % data_update_interval)

    # Check whether the wallet is locked
    if Two1Wallet.is_locked(wallet_path):
        wallet['locked'] = True
        logger.info("Wallet is locked.")
    else:
        logger.info("Wallet unlocked. Loading ...")
        try:
            load_wallet(wallet_path=wallet_path,
                        data_provider=ctx.obj['data_provider'],
                        passphrase="")
            logger.info("... loading complete.")
        except WalletNotLoadedError as e:
            logger.error(str(e))
            logger.info("Terminating.")
            sys.exit(-1)

    # Setup a signal handler
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    server_thread = threading.Thread(target=rpc_server.serve_forever,
                                     daemon=True)
    update_thread = threading.Thread(target=data_updater,
                                     daemon=True)
    server_thread.start()
    update_thread.start()
    logger.info("Daemon started.")
    server_thread.join()

    rpc_server.server_close()

    try:
        _check_wallet_loaded()
        wallet['obj'].sync_wallet_file(force_cache_write=True)
    except:
        pass

    sys.exit(0)


try:
    rpc_server = UnixSocketJSONRPCServer(dispatcher_methods=methods,
                                         client_lock=client_lock,
                                         request_cb=track_connections_cb,
                                         logger=logger)
except DaemonRunningError as e:
    click.echo(str(e))
    sys.exit(-1)

if __name__ == "__main__":
    main()
