import signal
import sys
import threading
import time

import click
from jsonrpcserver import Dispatcher
from jsonrpcserver.exceptions import ServerError

from two1.wallet.socket_rpc_server import UnixSocketJSONRPCServer
from two1.wallet.two1_wallet import Two1Wallet
from two1.wallet.two1_wallet_cli import validate_data_provider
from two1.wallet.two1_wallet_cli import WALLET_VERSION

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
DEF_WALLET_UPDATE_INTERVAL = 25  # seconds

dispatcher = Dispatcher()
rpc_server = UnixSocketJSONRPCServer(dispatcher)
wallet = dict(obj=None,
              locked=False,
              path=None,
              data_provider=None,
              update_interval=DEF_WALLET_UPDATE_INTERVAL)


def sig_handler(sig_num, stack_frame):
    print("Shutting down...")
    rpc_server.shutdown()


def data_updater():
    # This is a daemon thread so no need to explicitly
    # poll for any shutdown events.
    while True:
        if wallet['obj']:
            wallet['obj']._update_account_balances()
        time.sleep(wallet['update_interval'])


def load_wallet(wallet_path, data_provider, passphrase):
    global wallet

    wallet['obj'] = Two1Wallet(params_or_file=wallet_path,
                               data_provider=data_provider,
                               passphrase=passphrase)
    wallet['locked'] = False


def check_unlocked():
    if wallet['obj'] is None or wallet['locked']:
        raise ServerError("Wallet is locked. Use the 'unlock' command with the passphrase as an arg.")


@dispatcher.method('confirmed_balance')
def confirmed_balance():
    check_unlocked()
    return wallet['obj'].confirmed_balance()


@dispatcher.method('unconfirmed_balance')
def unconfirmed_balance():
    check_unlocked()
    return wallet['obj'].unconfirmed_balance()


@dispatcher.method('current_address')
def current_address():
    check_unlocked()
    return wallet['obj'].current_address


@dispatcher.method('send_to')
def send_to(address, amount, account):
    check_unlocked()
    return wallet['obj'].send_to(address, amount, account),


@dispatcher.method('unlock')
def unlock_wallet(passphrase):
    global wallet
    if not wallet['locked']:
        raise ServerError("Wallet is already unlocked or does not use a passphrase.")

    load_wallet(wallet_path=wallet['path'],
                data_provider=wallet['data_provider'],
                passphrase=passphrase)


@dispatcher.method('is_locked')
def is_locked():
    return wallet['locked']


@dispatcher.method('wallet_path')
def wallet_path():
    return wallet['path']


@dispatcher.method('sync_wallet_file')
def sync_wallet_file():
    return wallet['obj'].sync_wallet_file()


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option('--wallet-path', '-wp',
              default=Two1Wallet.DEFAULT_WALLET_PATH,
              type=click.Path(exists=True, resolve_path=True),
              show_default=True,
              help='Path to wallet file')
@click.option('--blockchain-data-provider', '-b',
              default='chain',
              type=click.Choice(['chain']),
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
@click.version_option(WALLET_VERSION)
@click.pass_context
def main(ctx, wallet_path, blockchain_data_provider,
         chain_api_key_id, chain_api_key_secret, data_update_interval):
    global wallet

    wallet['path'] = wallet_path
    if data_update_interval is not None:
        wallet['update_interval'] = data_update_interval

    # Check whether the wallet is locked
    if Two1Wallet.is_locked(wallet_path):
        wallet['locked'] = True
    else:
        load_wallet(wallet_path=wallet_path,
                    data_provider=ctx.obj['data_provider'],
                    passphrase="")

    # Setup a signal handler
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    server_thread = threading.Thread(target=rpc_server.serve_forever,
                                     daemon=True)
    update_thread = threading.Thread(target=data_updater,
                                     daemon=True)
    server_thread.start()
    update_thread.start()
    server_thread.join()

    rpc_server.server_close()
    sys.exit(0)


if __name__ == "__main__":
    main()
