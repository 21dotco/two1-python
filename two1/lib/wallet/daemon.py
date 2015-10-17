import logging
import logging.handlers
import signal
import sys
import threading
import time

import click
from jsonrpcserver import Methods
from jsonrpcserver.exceptions import ServerError
from path import Path
from two1.lib.bitcoin.crypto import PublicKey
from two1.lib.bitcoin.crypto import HDPublicKey
from two1.lib.wallet.socket_rpc_server import UnixSocketJSONRPCServer
from two1.lib.wallet.exceptions import AccountCreationError
from two1.lib.wallet.exceptions import WalletBalanceError
from two1.lib.wallet.two1_wallet import Two1Wallet
from two1.lib.wallet.two1_wallet_cli import validate_data_provider
from two1.lib.wallet.two1_wallet_cli import WALLET_VERSION

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
last_exception = None
wallet_dict_lock = threading.Lock()


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
    global last_exception

    last_exception = e
    logger.debug("exception: %s" % str(last_exception))
    raise ServerError(str(last_exception))


def do_update(block_on_acquire=True):
    """ Updates the wallet info.
    """
    if wallet['obj']:
        lock_acquired = False
        try:
            if wallet_dict_lock.acquire(block_on_acquire):
                lock_acquired = True
                logger.debug("Starting wallet update ...")
                wallet['obj']._update_account_balances()
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
        wallet['obj'] = Two1Wallet(params_or_file=wallet_path,
                                   data_provider=data_provider,
                                   passphrase=passphrase)
        wallet['locked'] = False
    except Exception:
        logger.exception("Wallet loading failed!")


def check_unlocked():
    """ Raises an error if the wallet is locked.
    """
    if wallet['obj'] is None or wallet['locked']:
        last_exception = "Wallet is locked. Use the 'unlock' command with the passphrase as an arg."
        raise ServerError()


@methods.add
def exception_info():
    """ RPC method to get info about the last exception.
    """
    return {'message': str(last_exception),
            'type': last_exception.__class__.__name__}


@methods.add
def confirmed_balance(account=None):
    """ RPC method to get the current confirmed balance.

    Returns:
        int: Current confirmed balance in satoshis.
    """
    check_unlocked()
    logger.debug("confirmed_balance(%r)" % (account))
    try:
        return wallet['obj'].confirmed_balance(account)
    except (ValueError, TypeError) as e:
        _handle_exception(e)


@methods.add
def unconfirmed_balance(account=None):
    """ RPC method to get the current unconfirmed balance.

    Returns:
        int: Current unconfirmed balance in satoshis.
    """
    check_unlocked()
    logger.debug("unconfirmed_balance(%r)" % (account))
    try:
        return wallet['obj'].unconfirmed_balance(account)
    except (ValueError, TypeError) as e:
        _handle_exception(e)


@methods.add
def get_private_for_public(public_key):
    """ RPC method to get the private key for the given public_key, if it is
        a part of this wallet.

    Args:
        public_key (str): Base58Check encoded serialization of the public key.

    Returns:
        str: A Base58Check encoded serialization of the private key object
           or None.
    """
    check_unlocked()
    w = wallet['obj']
    logger.debug("get_private_for_public(xx)")
    try:
        pub_key = HDPublicKey.from_b58check(public_key)
    except ValueError:
        pub_key = PublicKey.from_base64(public_key)
    priv_key = w.get_private_key(pub_key.address(testnet=w._testnet))

    return priv_key.to_b58check() if priv_key is not None else None


@methods.add
def current_address():
    """ RPC method to get the current payout address.

    Returns:
        str: Base58Check encoded bitcoin address.
    """
    check_unlocked()
    logger.debug("current_address()")
    try:
        return wallet['obj'].current_address
    except (ValueError, TypeError) as e:
        _handle_exception(e)


@methods.add
def get_change_address(account=None):
    """ RPC method to get the current change address.

    Returns:
        str: Base58Check encoded bitcoin address.
    """
    check_unlocked()
    logger.debug("get_change_address(%r)" % (account))
    try:
        return wallet['obj'].get_change_address(account)
    except (ValueError, TypeError) as e:
        _handle_exception(e)


@methods.add
def get_payout_address(account=None):
    """ RPC method to get the current payout address.

        This is an alias for current_address but allows
        passing in an account
    Returns:
        str: Base58Check encoded bitcoin address.
    """
    check_unlocked()
    logger.debug("get_payout_address(%r)" % (account))
    try:
        return wallet['obj'].get_payout_address(account)
    except (ValueError, TypeError) as e:
        _handle_exception(e)


@methods.add
def get_change_public_key(account=None):
    """ RPC method to get the current change public key.

    Returns:
        str: A Base58Check encoded serialization of the public key
    """
    check_unlocked()
    logger.debug("get_change_public_key(%r)" % (account))
    try:
        return wallet['obj'].get_change_public_key(account).to_b58check()
    except (ValueError, TypeError) as e:
        _handle_exception(e)


@methods.add
def get_payout_public_key(account=None):
    """ RPC method to get the current payout public key.

    Returns:
        str: A Base58Check encoded serialization of the public key
    """
    check_unlocked()
    logger.debug("get_payout_public_key(%r)" % (account))
    try:
        return wallet['obj'].get_payout_public_key(account).to_b58check()
    except (ValueError, TypeError) as e:
        _handle_exception(e)


@methods.add
def build_signed_transaction(addresses_and_amounts, use_unconfirmed=False,
                             fees=None, accounts=[]):
    """ RPC method to build and sign a transaction.

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
    check_unlocked()
    logger.debug("build_signed_transaction(%r, %r, %r, %r)" %
                 (addresses_and_amounts,
                  use_unconfirmed,
                  fees,
                  accounts))
    try:
        txns = wallet['obj'].build_signed_transaction(addresses_and_amounts,
                                                      use_unconfirmed,
                                                      fees,
                                                      accounts)
        txns_hex = [t.to_hex() for t in txns]
        logger.debug("txns: %r" % (txns_hex))
        return txns_hex
    except Exception as e:
        _handle_exception(e)


@methods.add
def make_signed_transaction_for(address, amount,
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
    check_unlocked()
    w = wallet['obj']
    logger.debug("make_signed_transaction_for(%s, %d, %r, %r, %r)" %
                 (address,
                  amount,
                  use_unconfirmed,
                  fees,
                  accounts))
    try:
        txns = w.make_signed_transaction_for(address, amount,
                                             use_unconfirmed,
                                             fees,
                                             accounts)
        logger.debug("txns: %r" % ([t['txid'] for t in txns]))

        return txns
    except Exception as e:
        _handle_exception(e)


@methods.add
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
    check_unlocked()
    logger.debug("send_to(%s, %d, %r, %r, %r)" %
                 (address,
                  amount,
                  use_unconfirmed,
                  fees,
                  accounts))
    try:
        txns = wallet['obj'].send_to(address=address,
                                     amount=amount,
                                     use_unconfirmed=use_unconfirmed,
                                     fees=fees,
                                     accounts=accounts)
        logger.debug("txns: %r" % ([t['txid'] for t in txns]))

        return txns
    except Exception as e:
        _handle_exception(e)


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


@methods.add
def is_locked():
    """ RPC method to determine whether the wallet is currently locked.

    Returns:
        bool: True if the wallet is locked, False if not.
    """
    return wallet['locked']


@methods.add
def wallet_path():
    """ RPC method to return the wallet path of the currently loaded wallet.

    Returns:
        str: The path to the currently loaded wallet.
    """
    return wallet['path']


@methods.add
def sync_wallet_file():
    """ RPC method to trigger a write to the wallet file.
    """
    try:
        return wallet['obj'].sync_wallet_file()
    except Exception as e:
        _handle_exception(e)


@methods.add
def create_account(name):
    """ RPC method to create an account
    """
    logger.debug("create_account(%r)" % (name))
    try:
        return wallet['obj'].create_account(name)
    except AccountCreationError as e:
        _handle_exception(e)


@methods.add
def account_names():
    """ RPC method to return all account names
    """
    return wallet['obj'].account_names


@methods.add
def sweep(address, accounts=[]):
    """ RPC method to sweep balance to a single address
    """
    logger.debug("sweep(%s, %r)" % (address, accounts))
    try:
        return wallet['obj'].sweep(address, accounts)
    except WalletBalanceError as e:
        _handle_exception(e)


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
        '%(asctime)s %(levelname)s: %(message)s')
    ch.setFormatter(ch_formatter)
    logger.addHandler(ch)

    logger.setLevel('DEBUG' if debug else 'INFO')

    global wallet

    wallet['path'] = wallet_path
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
        load_wallet(wallet_path=wallet_path,
                    data_provider=ctx.obj['data_provider'],
                    passphrase="")
        logger.info("... loading complete.")

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
    sys.exit(0)


if __name__ == "__main__":
    rpc_server = UnixSocketJSONRPCServer(methods,
                                         track_connections_cb)
    main()
