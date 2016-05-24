import functools
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
from two1.wallet import daemonizable
from two1.wallet.socket_rpc_server import UnixSocketJSONRPCServer
from two1.wallet.exceptions import DaemonRunningError
from two1.wallet.exceptions import WalletLockedError
from two1.wallet.exceptions import WalletNotLoadedError
from two1.wallet.two1_wallet import Two1Wallet
from two1.wallet.two1_wallet import Wallet
from two1.wallet.cli import validate_data_provider
import two1

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
    rpc_server.STOP_EVENT.set()
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
                wallet['obj'].sync_accounts()
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


def local_daemon_method(f):
    """ Decorator function to create a daemon method.

    Args:
        f (function): The function to make a daemon method

    Returns:
        function: A wrapper function
    """
    def wrapper(params):
        return f(*params['args'], **params['kwargs'])

    methods.add(wrapper, f.__name__)

    return wrapper


def _call_daemon_method(method_name, is_property, params):
    _check_wallet_loaded()
    logger.debug("%s(%r, %r)" % (method_name,
                                 params['args'],
                                 params['kwargs']))
    try:
        attr = getattr(wallet['obj'], method_name)
        if is_property:
            return attr
        else:
            args, kwargs = daemonizable.serdes_args(
                False, Two1Wallet, method_name,
                *params['args'], **params['kwargs'])

            return daemonizable.serdes_return_value(
                True, Two1Wallet, method_name,
                attr(*args, **kwargs))
    except Exception as e:
        _handle_exception(e)


def create_daemon_methods():
    daemon_methods = daemonizable.get_daemon_methods(Two1Wallet)
    for method_name, md in daemon_methods.items():
        p = functools.partial(_call_daemon_method, method_name, False)
        methods.add(p, method_name)

    daemon_properties = daemonizable.get_daemon_properties(Two1Wallet)
    for prop in daemon_properties:
        p = functools.partial(_call_daemon_method, prop, True)
        methods.add(p, prop)


@local_daemon_method
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


@local_daemon_method
def is_locked():
    """ RPC method to determine whether the wallet is currently locked.

    Returns:
        bool: True if the wallet is locked, False if not.
    """
    return wallet['locked']


@local_daemon_method
def wallet_path():
    """ RPC method to return the wallet path of the currently loaded wallet.

    Returns:
        str: The path to the currently loaded wallet.
    """
    return wallet['path']


@local_daemon_method
def sync_accounts():
    """ RPC method to trigger an update
    """
    _check_wallet_loaded()
    do_update()


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--wallet-path', '-wp',
              default=Two1Wallet.DEFAULT_WALLET_PATH,
              type=click.Path(exists=True, resolve_path=True),
              show_default=True,
              help='Path to wallet file')
@click.option('--blockchain-data-provider', '-b',
              default='twentyone',
              type=click.Choice(['twentyone', 'insight']),
              show_default=True,
              callback=validate_data_provider,
              help='Blockchain data provider service to use')
@click.option('--insight-url', '-iu',
              metavar='URL',
              envvar='INSIGHT_URL',
              is_eager=True,
              help='Insight Host URL (only if -b insight)')
@click.option('--insight-api-path', '-ip',
              metavar='STRING',
              envvar='INSIGHT_API_PATH',
              is_eager=True,
              help='Insight API path (only if -b insight)')
@click.option('--data-update-interval', '-u',
              type=click.IntRange(min=10, max=30),
              default=DEF_WALLET_UPDATE_INTERVAL,
              show_default=True,
              help='How often to update wallet data (seconds)')
@click.option('--debug', '-d',
              is_flag=True,
              help='Sets the logging level to debug')
@click.version_option(two1.TWO1_VERSION, message=two1.TWO1_VERSION_MESSAGE)
@click.pass_context
def main(ctx, wallet_path, blockchain_data_provider,
         insight_url, insight_api_path,
         data_update_interval, debug):
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

    create_daemon_methods()

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
    rpc_server = UnixSocketJSONRPCServer(
        socket_file_name=Wallet.SOCKET_FILE_NAME,
        dispatcher_methods=methods,
        client_lock=client_lock,
        request_cb=track_connections_cb,
        logger=logger)
except DaemonRunningError as e:
    click.echo(str(e))
    sys.exit(-1)

if __name__ == "__main__":
    main()
