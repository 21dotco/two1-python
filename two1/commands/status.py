"""
View the status of mining and machine-payable purchases
"""
# standard python imports
import urllib.parse
import collections
import logging

# 3rd party imports
import click

# two1 imports
import two1.channels as channels
from two1.channels.cli import format_expiration_time
from two1.commands.util import decorators
from two1.commands.util import uxstring
from two1.commands.util import bitcoin_computer

Balances = collections.namedtuple('Balances', ['twentyone', 'onchain', 'pending', 'flushed', 'channels'])


# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command("status")
@click.option("--detail",
              is_flag=True,
              default=False,
              help="List non-zero balances for each address")
@click.pass_context
@decorators.catch_all
@decorators.json_output
@decorators.capture_usage
@decorators.check_notifications
def status(ctx, detail):
    """View your bitcoin balance and address.
    """
    return _status(ctx.obj['config'], ctx.obj['client'], ctx.obj['wallet'], detail)


def _status(config, client, wallet, detail):
    """ Reports two1 status including balances, username, and mining hashrate

    Args:
        config (Config): config object used for getting .two1 information
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        wallet (two1.wallet.Wallet): a user's wallet instance
        detail (bool): Lists all balance details in status report

    Returns:
        dict: a dictionary of 'account', 'mining', and 'wallet' items with formatted
            strings for each value
    """
    status_dict = {
        "account": status_account(config, wallet),
        "mining": status_mining(client),
        "wallet": status_wallet(client, wallet, detail)
    }

    return status_dict


def status_mining(client):
    """ Prints the mining status if the device has a mining chip

    Args:
        client (TwentyOneRestClient): rest client used for communication with the backend api

    Returns:
        dict: a dictionary containing 'is_mining', 'hashrate', and 'mined' values
    """
    has_chip = bitcoin_computer.has_mining_chip()
    is_mining, mined, hashrate = None, None, None
    if has_chip:
        try:
            hashrate = bitcoin_computer.get_hashrate("15min")
            if hashrate > 0:
                hashrate = uxstring.UxString.status_mining_hashrate.format(hashrate/1e9)
            else:
                hashrate = uxstring.UxString.status_mining_hashrate_unknown
        except FileNotFoundError:
            is_mining = uxstring.UxString.status_mining_file_not_found
        except TimeoutError:
            is_mining = uxstring.UxString.status_mining_timeout
        else:
            is_mining = uxstring.UxString.status_mining_success

        mined = client.get_mined_satoshis()
        logger.info(uxstring.UxString.status_mining.format(is_mining, hashrate, mined))

    return dict(is_mining=is_mining, hashrate=hashrate, mined=mined)


def status_account(config, wallet):
    """ Logs a formatted string displaying account status to the command line

    Args:
        config (Config): config object used for getting .two1 information

    Returns:
        str: formatted string displaying account status
    """
    status_account_dict = {
        "username": config.username,
        "address": wallet.current_address
    }
    logger.info(uxstring.UxString.status_account.format(status_account_dict["username"]))
    return status_account_dict


def status_wallet(client, wallet, detail=False):
    """ Logs a formatted string displaying wallet status to the command line

    Args:
        client (TwentyOneRestClient): rest client used for communication with the backend api
        detail (bool): Lists all balance details in status report

    Returns:
        dict: a dictionary of 'wallet' and 'buyable' items with formatted
            strings for each value
    """
    channel_client = channels.PaymentChannelClient(wallet)
    user_balances = _get_balances(client, wallet, channel_client)

    status_wallet_dict = {
        "twentyone_balance": user_balances.twentyone,
        "onchain": user_balances.onchain,
        "flushing": user_balances.flushed,
        "channels_balance": user_balances.channels
    }
    logger.info(uxstring.UxString.status_wallet.format(**status_wallet_dict))

    if detail:
        # show balances by address for default wallet
        address_balances = wallet.balances_by_address(0)
        status_addresses = []
        for addr, balances in address_balances.items():
            if balances['confirmed'] > 0 or balances['total'] > 0:
                status_addresses.append(uxstring.UxString.status_wallet_address.format(
                    addr, balances['confirmed'], balances['total']))

        # Display status for all payment channels
        status_channels = []
        for url in channel_client.list():
            status_resp = channel_client.status(url)
            url = urllib.parse.urlparse(url)
            status_channels.append(uxstring.UxString.status_wallet_channel.format(
                url.scheme, url.netloc, status_resp .state, status_resp .balance,
                format_expiration_time(status_resp .expiration_time)))
        if not len(status_channels):
            status_channels = [uxstring.UxString.status_wallet_channels_none]

        logger.info(uxstring.UxString.status_wallet_detail_on.format(
            addresses=''.join(status_addresses), channels=''.join(status_channels)))
    else:
        logger.info(uxstring.UxString.status_wallet_detail_off)

    total_balance = user_balances.twentyone + user_balances.onchain

    if total_balance == 0:
        if bitcoin_computer.has_mining_chip():
            command = "21 mine"
        else:
            command = "21 earn"
        logger.info(uxstring.UxString.status_empty_wallet.format(
            click.style(command, bold=True)))
    else:
        buy21 = click.style("21 buy", bold=True)
        buy21help = click.style("21 buy --help", bold=True)
        logger.info(uxstring.UxString.status_exit_message.format(buy21, buy21help))

    return {
        "wallet": status_wallet_dict,
    }


def _get_balances(client, wallet, channel_client):
    balance_c = wallet.confirmed_balance()
    balance_u = wallet.unconfirmed_balance()
    pending_transactions = balance_u - balance_c

    spendable_balance = min(balance_c, balance_u)

    data = client.get_earnings()
    twentyone_balance = data["total_earnings"]
    flushed_earnings = data["flushed_amount"]

    channel_client.sync()
    channel_urls = channel_client.list()
    channels_balance = sum(s.balance for s in (channel_client.status(url) for url in channel_urls)
                           if s.state == channels.PaymentChannelState.READY)

    return Balances(twentyone_balance, spendable_balance, pending_transactions,
                    flushed_earnings, channels_balance)
