"""
View the status of mining and machine-payable purchases
"""
import click
# standard python imports
import urllib.parse
import collections

# 3rd party imports
import click
from tabulate import tabulate

# two1 imports
import two1.lib.channels as channels
from two1.lib.channels.cli import format_expiration_time
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST
from two1.lib.server.analytics import capture_usage
from two1.lib.util.decorators import json_output, check_notifications
from two1.lib.util.uxstring import UxString

Balances = collections.namedtuple('Balances', ['twentyone', 'onchain', 'pending', 'flushed', 'channels'])


def has_bitcoinkit():
    """ Check for presence of mining chip via file presence

    The full test is to actually try to boot the chip, but we
    only try that if this file exists.

    We keep this file in two1/commands/status to avoid a circular
    import.
    Todo:
        Move out of status

    Returns:
        bool: True if device is a bitcoin computer, false otherwise
    """
    try:
        with open("/proc/device-tree/hat/product", "r") as f:
            bitcoinkit_present = f.read().startswith('21 Bitcoin')
    except FileNotFoundError:
        bitcoinkit_present = False
    return bitcoinkit_present


def get_hashrate():
    """ Uses unix socks to get hashrate of mining chip on current system

    Returns:
        str: A formatted string showing the mining hashrate
    """
    hashrate = None

    try:
        import socket
        import json

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect("/tmp/minerd.sock")

        buf = b""

        while True:
            chunk = s.recv(4096)

            # If server disconnected
            if not chunk:
                s.close()
                break

            buf += chunk
            while b"\n" in buf:
                pos = buf.find(b"\n")
                data = buf[0:pos].decode('utf-8')
                buf = buf[pos+1:]

                event = json.loads(data)

                if event['type'] == "StatisticsEvent":
                    # Use 15min hashrate, if uptime is past 15min
                    if event['payload']['statistics']['uptime'] > 15*60:
                        hashrate = "{:.1f} GH/s".format(event['payload']['statistics']['hashrate']['15min']/1e9)
                    else:
                        hashrate = "~50 GH/s (warming up)"

                    break

            if hashrate:
                break
    except:
        pass

    return hashrate or UxString.Error.data_unavailable


def status_mining(config, client):
    """ Prints the mining status if the device has a mining chip

    Args:
        config (Config): config object used for getting .two1 information
        client (TwentyOneRestClient): rest client used for communication with the backend api

    Returns:
        dict: a dictionary containing 'is_mining', 'hashrate', and 'mined' values
    """
    has_chip = has_bitcoinkit()
    if has_chip:
        bk = "21 mining chip running (/run/minerd.pid)"
        mined = client.get_mined_satoshis()
        hashrate = get_hashrate()
        if hashrate == UxString.Error.data_unavailable:
            bk = "Run {} to start mining".format(click.style("21 mine", bold=True))
    else:
        bk, mined, hashrate = None, None, None
    data = dict(is_mining=bk,
                hashrate=hashrate,
                mined=mined)
    if has_chip:
        out = UxString.status_mining.format(**data)
        config.log(out)

    return data


@click.command("status")
@click.option("--detail",
              is_flag=True,
              default=False,
              help="List non-zero balances for each address")
@json_output
def status(config, detail):
    """View your bitcoin balance and address.
    """
    return _status(config, detail)


@capture_usage
@check_notifications
def _status(config, detail):
    """ Reports two1 stataus including balances, username, and mining hashrate

    Args:
        config (Config): config object used for getting .two1 information
        detail (bool): Lists all balance details in status report

    Returns:
        dict: a dictionary of 'account', 'mining', and 'wallet' items with formatted
            strings for each value
    """
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)


    status = {
        "account": status_account(config),
        "mining": status_mining(config, client),
        "wallet": status_wallet(config, client, detail)
    }

    config.log("")
    # status_endpoints(config)
    # status_bought_endpoints(config)

    return status

def status_account(config):
    """ Logs a formatted string displaying account status to the command line

    Args:
        config (Config): config object used for getting .two1 information

    Returns:
        str: formatted string displaying account status
    """
    status_account = {
        "username": config.username,
        "address": config.wallet.current_address
    }
    config.log(UxString.status_account.format(status_account["username"]))
    return status_account

SEARCH_UNIT_PRICE = 3500
SMS_UNIT_PRICE = 3000


def status_wallet(config, client, detail=False):
    """ Logs a formatted string displaying wallet status to the command line

    Args:
        config (Config): config object used for getting .two1 information
        client (TwentyOneRestClient): rest client used for communication with the backend api
        detail (bool): Lists all balance details in status report

    Returns:
        dict: a dictionary of 'wallet' and 'buyable' items with formatted
            strings for each value
    """
    user_balances = _get_balances(config, client)

    status_wallet = {
        "twentyone_balance": user_balances.twentyone,
        "onchain": user_balances.onchain,
        "flushing": user_balances.flushed,
        "channels_balance": user_balances.channels
    }
    config.log(UxString.status_wallet.format(**status_wallet))

    if detail:
        # show balances by address for default wallet
        address_balances = config.wallet.balances_by_address(0)
        status_addresses = []
        for addr, balances in address_balances.items():
            if balances['confirmed'] > 0 or balances['total'] > 0:
                status_addresses.append(UxString.status_wallet_address.format(
                    addr, balances['confirmed'], balances['total']))

        # Display status for all payment channels
        status_channels = []
        for url in config.channel_client.list():
            status = config.channel_client.status(url)
            url = urllib.parse.urlparse(url)
            status_channels.append(UxString.status_wallet_channel.format(
                url.scheme, url.netloc, status.state, status.balance,
                format_expiration_time(status.expiration_time)))
        if not len(status_channels):
            status_channels = [UxString.status_wallet_channels_none]

        config.log(UxString.status_wallet_detail_on.format(
            addresses=''.join(status_addresses), channels=''.join(status_channels)))
    else:
        config.log(UxString.status_wallet_detail_off)

    total_balance = user_balances.twentyone + user_balances.onchain
    buyable_searches = int(total_balance / SEARCH_UNIT_PRICE)
    buyable_sms = int(total_balance / SMS_UNIT_PRICE)
    status_buyable = {
        "buyable_searches": buyable_searches,
        "search_unit_price": SEARCH_UNIT_PRICE,
        "buyable_sms": buyable_sms,
        "sms_unit_price": SMS_UNIT_PRICE
    }
    config.log(UxString.status_buyable.format(**status_buyable), nl=False)

    if total_balance == 0:
        config.log(UxString.status_empty_wallet.format(click.style("21 mine",
                                                                   bold=True)))
    else:
        buy21 = click.style("21 buy", bold=True)
        buy21help = click.style("21 buy --help", bold=True)
        config.log(UxString.status_exit_message.format(buy21, buy21help),
                   nl=False)

    return {
        "wallet" : status_wallet,
        "buyable": status_buyable
    }


def _get_balances(config, client):
    balance_c = config.wallet.confirmed_balance()
    balance_u = config.wallet.unconfirmed_balance()
    pending_transactions = balance_u - balance_c

    spendable_balance = min(balance_c, balance_u)

    data = client.get_earnings()
    twentyone_balance = data["total_earnings"]
    flushed_earnings = data["flushed_amount"]
    config.channel_client.sync()
    channel_urls = config.channel_client.list()
    channels_balance = sum(s.balance for s in (config.channel_client.status(url) for url in channel_urls)
                           if s.state == channels.PaymentChannelState.READY)

    return Balances(twentyone_balance, spendable_balance, pending_transactions,
                    flushed_earnings, channels_balance)


def status_earnings(config, client):
    """ Logs a formatted string displaying earnings status to the command line

    Args:
        config (Config): config object used for getting .two1 information
        client (TwentyOneRestClient): rest client used for communication with the backend api
    """
    data = client.get_earnings()
    total_earnings = data["total_earnings"]
    total_payouts = data["total_payouts"]
    config.log('\nMining Proceeds', fg='magenta')
    config.log('''
    Total Earnings           : {}
    Total Payouts            : {}''' .format(none2zero(total_earnings), none2zero(total_payouts)))

    if "flush_amount" in data and data["flush_amount"] > 0:
        flush_amount = data["flush_amount"]
        config.log("Flushed Earnings         : {}" .format(none2zero(flush_amount)))
        config.log("\n" + UxString.flush_status % flush_amount, fg='green')


def status_shares(config, client):
    """ Logs a formatted string displaying shares status to the command line

    Args:
        config (Config): config object used for getting .two1 information
        client (TwentyOneRestClient): rest client used for communication with the backend api
    """
    try:
        share_data = client.get_shares()
    except:
        share_data = None
    headers = ("", "Total", "Today", "Past Hour")
    data = []

    if share_data:
        try:
            for n in ["good", "bad"]:
                data.append(map(none2zero, [n, share_data["total"][n],
                                            share_data["today"][n],
                                            share_data["hour"][n]]))
        except KeyError:
            data = []  # config.log(UxString.Error.data_unavailable)

        if len(data):
            config.log("\nShare statistics:", fg="magenta")
            config.log(tabulate(data, headers=headers, tablefmt='psql'))
            # else:
            #    config.log(UxString.Error.data_unavailable)


def none2zero(x):
    """ function to map None values of shares to 0 """
    return 0 if x is None else x
