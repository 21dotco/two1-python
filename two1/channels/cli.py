"""Command-line interface for managing client-side payment channel management."""
import click
import collections
import json
import time
import sys
import os

import two1
from two1.wallet import Wallet, Two1Wallet

from . import PaymentChannelClient
from . import PaymentChannelError
from . import PaymentChannelState


CHANNELS_DB_PATH = os.environ.get("CHANNELS_DB_PATH", PaymentChannelClient.DEFAULT_CHANNELS_DB_PATH)
WALLET_PATH = os.environ.get("WALLET_PATH", Two1Wallet.DEFAULT_WALLET_PATH)

COLORS = {
    "black": "\x1b[1;30m",
    "red": "\x1b[1;31m",
    "green": "\x1b[1;32m",
    "yellow": "\x1b[1;33m",
    "blue": "\x1b[1;34m",
    "magenta": "\x1b[1;35m",
    "cyan": "\x1b[1;36m",
    "white": "\x1b[1;37m",
    "reset": "\x1b[0m"
}


def format_state(state):
    """Colorize string representation of payment channel state.

    Args:
        state (str): String representation of payment channel state.

    Returns:
        str: Colorized payment channel state.

    """
    if state == str(PaymentChannelState.READY):
        return COLORS['green'] + str(state) + COLORS['reset']
    elif state in (str(PaymentChannelState.CONFIRMING_DEPOSIT), str(PaymentChannelState.CONFIRMING_SPEND)):
        return COLORS['magenta'] + str(state) + COLORS['reset']
    elif state == str(PaymentChannelState.CLOSED):
        return COLORS['red'] + str(state) + COLORS['reset']
    else:
        return str(state)


def format_expiration_time(expires):
    """Format expiration time in terms of days, hours, minutes, and seconds.

    Args:
        expires (int): Absolute UNIX time.

    Returns:
        str: Human-readable expiration time in terms of days, hours, minutes,
            and seconds.

    """
    delta = int(expires - time.time())

    if delta < 0:
        return "Expired at " + time.asctime(time.localtime(expires))

    days, r = divmod(delta, 86400)
    hours, r = divmod(r, 3600)
    minutes, r = divmod(r, 60)
    seconds = r

    if days > 0:
        return "{} days, {} hrs, {} min, {} sec".format(days, hours, minutes, seconds)
    elif hours > 0:
        return "{} hrs, {} min, {} sec".format(hours, minutes, seconds)
    elif minutes > 0:
        return "{} min, {} sec".format(minutes, seconds)
    else:
        return "{} sec".format(seconds)


@click.group('channels', context_settings={'help_option_names': ['-h', '--help']})
@click.option("--json", is_flag=True, default=False, help="JSON output.")
@click.version_option(two1.TWO1_VERSION, message=two1.TWO1_VERSION_MESSAGE)
@click.pass_context
def main(ctx, json):
    """Manage payment channels.

    The `21 channels` command is used for creating, opening, closing, and conducting
    diagnostics for the payment channel micropayments protocol. After opening
    a channel with a merchant, making a payment returns a token, which the
    merchant will accept as proof of payment within the 402 payments protocol.
    Example of opening a channel, making payments, and closing the channel:

    $ channels open https://mkt.21.co/21dotco/payments/channel 100000 120\n
    $ channels pay https://mkt.21.co/21dotco/payments/channel 100\n
    $ channels pay https://mkt.21.co/21dotco/payments/channel 100\n
    $ channels pay https://mkt.21.co/21dotco/payments/channel 100\n
    $ channels info https://mkt.21.co/21dotco/payments/channel\n
    $ channels close https://mkt.21.co/21dotco/payments/channel\n
    """
    client = PaymentChannelClient(Wallet(WALLET_PATH), CHANNELS_DB_PATH)
    ctx.obj = {'client': client, 'json': json}


@click.command('sync', help="Sync channels.")
@click.pass_context
def cli_sync(ctx):
    """Synchronize payment channels."""
    ctx.obj['client'].sync()


@click.command('list', help="List channels.")
@click.pass_context
def cli_list(ctx):
    """List payment channels and their information."""
    urls = ctx.obj['client'].list()

    if ctx.obj['json']:
        print(json.dumps({'result': urls}))
    elif len(urls) == 0:
        print("No payment channels exist.")
    else:
        print()
        for url in urls[::-1]:
            print(COLORS['blue'] + url + COLORS['reset'])
            # Get channel status
            status = ctx.obj['client'].status(url)
            print("    {:<16}{}".format("Status", format_state((str(status.state)))))
            print("    {:<16}{}".format("Balance", status.balance))
            print("    {:<16}{}".format("Deposit", status.deposit))
            print("    {:<16}{}".format("Created", time.asctime(time.localtime(status.creation_time))))
            print("    {:<16}{}".format("Expires", format_expiration_time(status.expiration_time)))
            print("    {:<16}{}".format("Deposit txid", status.deposit_txid))
            print("    {:<16}{}".format("Spend txid", status.spend_txid))
            print()


@click.command('open', help="Open channel.")
@click.pass_context
@click.argument('url', type=click.STRING)
@click.argument('deposit', type=click.INT)
@click.argument('expiration', type=click.INT)
@click.option('--fee', default=10000, help="Fee amount in satoshis.")
@click.option('--zeroconf', default=False, is_flag=True,
              help="Use payment channel without deposit confirmation. This preference " +
              "will be overriden by server configuration if applicable.")
@click.option('--use-unconfirmed', default=False, is_flag=True,
              help="Use unconfirmed transactions to build deposit transaction.")
def cli_open(ctx, url, deposit, expiration, fee, zeroconf, use_unconfirmed):
    """Open a payment channel at the specified URL.

    Args:
        url (str): Payment channel server URL.
        deposit (int): Deposit amount in satoshis
        expiration (int): Relative expiration time in seconds
        fee (int): Fee in in satoshis
        zeroconf (bool): Use payment channel without deposit confirmation.
        use_unconfirmed (bool): Use unconfirmed transactions to build
            deposit transaction.

    """
    # Open channel
    try:
        url = ctx.obj['client'].open(url, deposit, expiration, fee, zeroconf, use_unconfirmed)
    except PaymentChannelError as e:
        if ctx.obj['json']:
            print(json.dumps({'error': str(e)}))
        else:
            print("Error: " + str(e))
        sys.exit(1)

    if ctx.obj['json']:
        print(json.dumps({'result': url}))
    else:
        # Get channel status
        status = ctx.obj['client'].status(url)
        print("Opened {}".format(status.url))
        print("Deposit txid {}".format(status.deposit_txid))
        print("Balance: {}. Deposit: {}. Expires in {}.".format(status.balance, status.deposit, format_expiration_time(
            status.expiration_time)))


@click.command('pay', help="Create payment to channel.")
@click.pass_context
@click.argument('url', type=click.STRING)
@click.argument('amount', type=click.INT)
def cli_pay(ctx, url, amount):
    """Pay to a payment channel.

    Args:
        url (str): Payment channel URL.
        amount (int): Amount to pay in satoshis.

    """
    # Look up url
    url = next(iter(ctx.obj['client'].list(url)), None)
    if not url:
        if ctx.obj['json']:
            print(json.dumps({'error': 'Channel not found.'}))
        else:
            print("Error: Channel not found.")
        sys.exit(1)

    # Pay to channel
    try:
        txid = ctx.obj['client'].pay(url, amount)
    except PaymentChannelError as e:
        if ctx.obj['json']:
            print(json.dumps({'error': str(e)}))
        else:
            print("Error: " + str(e))
        sys.exit(1)

    if ctx.obj['json']:
        print(json.dumps({'result': txid}))
    else:
        print(txid)


@click.command('status', help="Get status of channel.")
@click.pass_context
@click.argument('url', type=click.STRING)
def cli_status(ctx, url):
    """Get status and basic information of a payment channel.

    Args:
        url (str): Payment channel URL.

    """
    # Look up url
    url = next(iter(ctx.obj['client'].list(url)), None)
    if not url:
        if ctx.obj['json']:
            print(json.dumps({'error': 'Channel not found.'}))
        else:
            print("Error: Channel not found.")
        sys.exit(1)

    # Get channel status
    status = ctx.obj['client'].status(url)

    if ctx.obj['json']:
        print(json.dumps(
            {'result': {
                'url': status.url,
                'state': str(status.state),
                'ready': status.ready,
                'balance': status.balance,
                'deposit': status.deposit,
                'creation_time': status.creation_time,
                'expiration_time': status.expiration_time,
                'expired': status.expired,
                'deposit_txid': status.deposit_txid,
                'spend_txid': status.spend_txid
            }}))
    else:
        print("{}. Balance: {}. Deposit: {}. Expires in {}.".format(
            format_state(str(status.state)), status.balance, status.deposit, format_expiration_time(
                status.expiration_time)))


@click.command('info', help="Get details of channel.")
@click.pass_context
@click.argument('url', type=click.STRING)
def cli_info(ctx, url):
    """Get status and detailed information of a payment channel.

    Args:
        url (str): Payment channel URL.

    """
    # Look up url
    url = next(iter(ctx.obj['client'].list(url)), None)
    if not url:
        if ctx.obj['json']:
            print(json.dumps({'error': 'Channel not found.'}))
        else:
            print("Error: Channel not found.")
        sys.exit(1)

    # Get channel status
    status = ctx.obj['client'].status(url, include_txs=True)

    if ctx.obj['json']:
        print(json.dumps(
            {'result': {
                'url': status.url,
                'state': str(status.state),
                'ready': status.ready,
                'balance': status.balance,
                'deposit': status.deposit,
                'creation_time': status.creation_time,
                'expiration_time': status.expiration_time,
                'expired': status.expired,
                'deposit_txid': status.deposit_txid,
                'spend_txid': status.spend_txid,
                'transactions': {
                    'deposit_tx': status.transactions.deposit_tx,
                    'refund_tx': status.transactions.refund_tx,
                    'payment_tx': status.transactions.payment_tx,
                    'spend_tx': status.transactions.spend_tx
                }
            }}
        ))
    else:
        print()
        print(COLORS['blue'] + status.url + COLORS['reset'])
        print("    {:<16}{}".format("Status", format_state(str(status.state))))
        print("    {:<16}{}".format("Balance", status.balance))
        print("    {:<16}{}".format("Deposit", status.deposit))
        print("    {:<16}{}".format("Created", time.asctime(time.localtime(status.creation_time))))
        print("    {:<16}{}".format("Expires", format_expiration_time(status.expiration_time)))
        print("    {:<16}{}".format("Deposit txid", status.deposit_txid))
        print("    {:<16}{}".format("Spend txid", status.spend_txid))
        print()
        print("    Transactions")
        print("         Deposit tx")
        print("             {}".format(status.transactions.deposit_tx))
        print("         Refund tx")
        print("             {}".format(status.transactions.refund_tx))
        print("         Payment tx (half-signed)")
        print("             {}".format(status.transactions.payment_tx))
        print("         Spend Tx")
        print("             {}".format(status.transactions.spend_tx))
        print()


@click.command('close', help="Close channel.")
@click.pass_context
@click.argument('url', type=click.STRING)
def cli_close(ctx, url):
    """Close a payment channel.

    Args:
        url (str): Payment channel URL.

    """
    # Look up url
    url = next(iter(ctx.obj['client'].list(url)), None)
    if not url:
        if ctx.obj['json']:
            print(json.dumps({'error': 'Channel not found.'}))
        else:
            print("Error: Channel not found.")
        sys.exit(1)

    # Close channel
    try:
        ctx.obj['client'].close(url)
    except PaymentChannelError as e:
        if ctx.obj['json']:
            print(json.dumps({'error': str(e)}))
        else:
            print("Error: " + str(e))
        sys.exit(1)

    # Get channel status
    status = ctx.obj['client'].status(url)

    if ctx.obj['json']:
        print(json.dumps(
            {'result': {
                'url': status.url,
                'state': str(status.state),
                'ready': status.ready,
                'balance': status.balance,
                'deposit': status.deposit,
                'expiration_time': status.expiration_time,
                'expired': status.expired,
                'deposit_txid': status.deposit_txid,
                'spend_txid': status.spend_txid
            }}))
    else:
        print("Channel closed. Balance: {}. Deposit: {}.".format(status.balance, status.deposit))
        print("Expected spend txid {}".format(status.spend_txid))


@click.command('help', help="Print help.")
@click.pass_context
def cli_help(ctx):
    """Get payment CLI help."""
    print(ctx.parent.get_help())


main.commands = collections.OrderedDict()
main.list_commands = lambda ctx: main.commands
main.add_command(cli_list)
main.add_command(cli_sync)
main.add_command(cli_open)
main.add_command(cli_pay)
main.add_command(cli_status)
main.add_command(cli_info)
main.add_command(cli_close)
main.add_command(cli_help)

if __name__ == "__main__":
    main()
