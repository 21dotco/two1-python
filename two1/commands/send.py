""" Two1 command to send bitcoin to another address """
# standart python imports
import logging

# 3rd party imports
import click

# two1 imports
from two1.blockchain.exceptions import DataProviderError
from two1.wallet.exceptions import WalletBalanceError
from two1.commands.util import decorators
from two1.commands.util import uxstring
from two1.commands.util import exceptions
from two1.commands.util import currency
from two1.commands.util.bitcoin_computer import has_mining_chip

# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command("send")
@click.argument('address', type=click.STRING)
@click.argument('amount', type=click.FLOAT)
@click.argument('denomination', default='', type=click.STRING)
@click.option('--use-unconfirmed', '-u',
              is_flag=True,
              default=False,
              show_default=True,
              help="Use unconfirmed transactions/UTXOs")
@click.option('--verbose', '-v', is_flag=True, default=False,
              help="Show all transaction inputs and outputs.")
@click.pass_context
@decorators.catch_all
def send(ctx, address, amount, denomination, use_unconfirmed, verbose):
    """Send a specified address some satoshis.

\b
Usage
-----
Send 5000 satoshi from your on-chain balance to the Apache Foundation.
$ 21 send 1BtjAzWGLyAavUkbw3QsyzzNDKdtPXk95D 5000 satoshis

You can use the following denominations: satoshis, bitcoins, and USD.

By default, this command uses only confirmed transactions and
UTXOs to send coins. To use unconfirmed transactions, use the
--use-unconfirmed flag.
"""
    if denomination == '':
        confirmed = click.confirm(uxstring.UxString.default_price_denomination, default=True)
        if not confirmed:
            raise exceptions.Two1Error(uxstring.UxString.cancel_command)
        denomination = currency.Price.SAT
    price = currency.Price(amount, denomination)
    return _send(ctx.obj['wallet'], address, price.satoshis, verbose, use_unconfirmed)


def _send(wallet, address, satoshis, verbose, use_unconfirmed=False):
    """Send bitcoin to the specified address"""
    txids = []
    try:
        txids = wallet.send_to(address=address, amount=satoshis, use_unconfirmed=use_unconfirmed)
        # For now there is only a single txn created, so assume it's 0
        txid, txn = txids[0]["txid"], txids[0]["txn"]
        if verbose:
            logger.info(uxstring.UxString.send_success_verbose.format(satoshis, address, txid, txn))
        else:
            logger.info(uxstring.UxString.send_success.format(satoshis, address, txid))
    except ValueError as e:
        # This will trigger if there's a below dust-limit output.
        raise exceptions.Two1Error(str(e))
    except WalletBalanceError as e:
        if wallet.unconfirmed_balance() > satoshis:
            raise exceptions.Two1Error(uxstring.UxString.send_insufficient_confirmed + str(e))
        else:
            balance = min(wallet.confirmed_balance(), wallet.unconfirmed_balance())
            if has_mining_chip():
                raise exceptions.Two1Error(uxstring.UxString.send_insufficient_blockchain_21bc.format(
                    balance, satoshis, address))
            else:
                raise exceptions.Two1Error(uxstring.UxString.send_insufficient_blockchain_free.format(
                    balance, satoshis, address))
    except DataProviderError as e:
        if "rejected" in str(e):
            raise exceptions.Two1Error(uxstring.UxString.send_rejected)
        else:
            raise exceptions.Two1Error(str(e))
    return txids
