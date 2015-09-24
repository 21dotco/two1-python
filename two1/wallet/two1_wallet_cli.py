import click
import getpass
import types

from two1.blockchain.chain_provider import ChainProvider
from two1.wallet.account_types import account_types
from two1.wallet.base_wallet import satoshi_to_btc
from two1.wallet.two1_wallet import Two1Wallet
from two1.wallet.daemonizer import get_daemonizer
from two1.wallet.socket_rpc_server import UnixSocketServerProxy
from two1.wallet import exceptions

WALLET_VERSION = "0.1.0"
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])
REQUIRED_DATA_PROVIDER_PARAMS = {'chain': ['chain_api_key_id', 'chain_api_key_secret']}


def get_passphrase():
    return getpass.getpass("Passphrase to unlock wallet: ")


def check_daemon_running(wallet_path):
    rv = None
    try:
        w = UnixSocketServerProxy()

        # Check the path to make sure it's the same
        wp = w.wallet_path()
        rv = w if wp == wallet_path else None

    except exceptions.DaemonNotRunningError:
        rv = None

    return rv


def check_wallet_proxy_unlocked(w, passphrase):
    if w.is_locked():
        if not passphrase:
            click.echo("The wallet is locked and requires a passphrase.")
            passphrase = get_passphrase()

        w.unlock(p)

    return not w.is_locked()


def _call_wallet_method(wallet, method_name, *args, **kwargs):
    rv = None
    if hasattr(wallet, method_name):
        attr = getattr(wallet, method_name)
        if isinstance(attr, types.FunctionType) or \
           isinstance(attr, types.MethodType):
            rv = attr(*args, **kwargs)
        else:
            rv = attr
    else:
        raise exceptions.UndefinedMethodError("wallet has no method or property: %s" % method_name)

    return rv

@click.pass_context
def validate_data_provider(ctx, param, value):
    data_provider_params = {}
    if ctx.obj is None:
        ctx.obj = {}

    if value not in REQUIRED_DATA_PROVIDER_PARAMS:
        ctx.fail("Unknown data provider %s" % value)

    required = REQUIRED_DATA_PROVIDER_PARAMS[value]

    fail = False
    for r in required:
        if r not in ctx.params:
            s = r.replace('_', '-')
            click.echo("--%s is required to use %s." % (s, value))
            fail = True
        else:
            data_provider_params[r] = ctx.params[r]

    if fail:
        ctx.fail("One or more required arguments are missing.")

    dp = None
    if value == 'chain':
        key = ctx.params['chain_api_key_id']
        secret = ctx.params['chain_api_key_secret']

        # validate key and secret for chain data provider
        if len(key) != 32 or len(secret) != 32 or \
           not key.isalnum() or not secret.isalnum():
            ctx.fail("Invalid chain_api_key_id or chain_api_key_secret")

        dp = ChainProvider(api_key_id=key, api_key_secret=secret)

    ctx.obj['data_provider'] = dp
    ctx.obj['data_provider_params'] = data_provider_params


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--wallet-path', '-wp',
              default=Two1Wallet.DEFAULT_WALLET_PATH,
              metavar='PATH',
              show_default=True,
              help='Path to wallet file')
@click.option('--passphrase', '-p',
              is_flag=True,
              help='Prompt for a passphrase.')
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
@click.version_option(WALLET_VERSION)
@click.pass_context
def main(ctx, wallet_path, passphrase,
         blockchain_data_provider, chain_api_key_id, chain_api_key_secret):
    """ Command-line Interface for the Two1 Wallet
    """
    if ctx.obj is None:
        ctx.obj = {}

    ctx.obj['wallet_path'] = wallet_path
    ctx.obj['passphrase'] = passphrase

    if ctx.invoked_subcommand not in ['create', 'startdaemon']:
        p = get_passphrase() if passphrase else ''

        # Check if the daemon is running
        w = check_daemon_running(wallet_path)
        if w is not None:
            ctx.obj['wallet'] = w
            check_wallet_proxy_unlocked(w, p)
        else:
            # instantiate a wallet object here and pass it into the context
            ctx.obj['wallet'] = Two1Wallet(params_or_file=wallet_path,
                                           data_provider=ctx.obj['data_provider'],
                                           passphrase=p)

            ctx.call_on_close(ctx.obj['wallet'].sync_wallet_file)


@click.command()
@click.pass_context
def startdaemon(ctx):
    """ Starts the daemon
    """
    d = get_daemonizer()
    if d is None:
        return

    if d.started():
        click.echo("walletd already running.")
        return

    if not d.installed():
        if isinstance(ctx.obj['data_provider'], ChainProvider):
            dp_params = ctx.obj['data_provider_params']
            dpo = dict(provider='chain',
                       api_key_id=dp_params['chain_api_key_id'],
                       api_key_secret=dp_params['chain_api_key_secret'])
            d.install(dpo)

    if d.start():
        click.echo("walletd successfully started.")


@click.command()
@click.pass_context
def stopdaemon(ctx):
    """ Stops the daemon
    """
    d = get_daemonizer()
    if d is None:
        return

    if d.stop():
        click.echo("walletd successfully stopped.")


@click.command()
@click.option('--account-type', '-a',
              default=Two1Wallet.DEFAULT_ACCOUNT_TYPE,
              type=click.Choice(list(account_types.keys())),
              show_default=True,
              help='Type of account to create')
@click.option('--testnet', '-tn',
              is_flag=True,
              help="Create a testnet wallet.")
@click.pass_context
def create(ctx, account_type, testnet):
    """ Creates a new wallet
    """
    # txn_data_provider and related params come from the
    # global context.
    passphrase = ""
    if ctx.obj['passphrase']:
        # Let's prompt for a passphrase
        conf = "a"
        i = 0
        while passphrase != conf and i < 3:
            passphrase = getpass.getpass("Enter desired passphrase: ")
            conf = getpass.getpass("Confirm passphrase: ")
            i += 1

        if passphrase != conf:
            ctx.fail("Passphrases don't match. Quitting.")

    options = {"account_type": account_type,
               "passphrase": passphrase,
               "data_provider": ctx.obj['data_provider'],
               "testnet": testnet,
               "wallet_path": ctx.obj['wallet_path']}

    created = Two1Wallet.configure(options)

    if created:
        click.echo("Wallet successfully created!")
    else:
        ctx.fail("Wallet was not created.")


@click.command(name="payoutaddress")
@click.pass_context
def payout_address(ctx):
    """ Prints the current payout address
    """
    w = ctx.obj['wallet']
    click.echo(_call_wallet_method(w, 'current_address'))


@click.command(name="confirmedbalance")
@click.pass_context
def confirmed_balance(ctx):
    """ Prints the current *confirmed* balance
    """
    w = ctx.obj['wallet']
    cb = _call_wallet_method(w, 'confirmed_balance')
    click.echo("Confirmed balance: %f BTC" %
               (cb / satoshi_to_btc))


@click.command()
@click.pass_context
def balance(ctx):
    """ Prints the current total balance.
    """
    w = ctx.obj['wallet']
    ucb = _call_wallet_method(w, 'unconfirmed_balance')
    click.echo("Total balance (including unconfirmed txns): %f BTC" %
               (ucb / satoshi_to_btc))


@click.command(name="sendto")
@click.argument('address',
                metavar="STRING")
@click.argument('amount',
                type=click.FLOAT)
@click.option('--account',
              metavar="STRING",
              multiple=True)
@click.pass_context
def send_to(ctx, address, amount, account):
    """ Send bitcoin to a single address
    """
    w = ctx.obj['wallet']

    # Do we want to confirm if it's larger than some amount?
    satoshis = int(amount * satoshi_to_btc)
    print("Sending %d satoshis to %s from accounts = %r" %
          (satoshis, address, list(account)))

    try:
        txids = _call_wallet_method(w, 'send_to',
                                    address=address,
                                    amount=satoshis,
                                    accounts=list(account))
        if txids:
            click.echo("Successfully sent %f BTC to %s. txid = %r" %
                       (amount, address, [t['txid'] for t in txids]))
    except Exception as e:
        click.echo("Problem sending coins: %s" % e)


main.add_command(startdaemon)
main.add_command(stopdaemon)
main.add_command(create)
main.add_command(payout_address)
main.add_command(confirmed_balance)
main.add_command(balance)
main.add_command(send_to)

if __name__ == "__main__":
    main()
