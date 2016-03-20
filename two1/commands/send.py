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


# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command("send")
@click.argument('address', type=click.STRING)
@click.argument('satoshis', type=click.INT)
@click.option('--use-unconfirmed', '-u',
              is_flag=True,
              default=False,
              show_default=True,
              help="Use unconfirmed transactions/UTXOs")
@decorators.catch_all
@decorators.json_output
def send(ctx, address, satoshis, use_unconfirmed):
    """Send the specified address some satoshis.

\b
Usage
-----
Mine bitcoin at 21.co, flush it to the Blockchain, and then send 5000
to the Apache Foundation.
$ 21 mine
$ 21 flush
# Wait ~10-20 minutes for flush to complete and block to mine
$ 21 send 1BtjAzWGLyAavUkbw3QsyzzNDKdtPXk95D 1000

By default, this command uses only confirmed transactions and
UTXOs to send coins. To use unconfirmed transactions, use the
--use-unconfirmed flag.
"""
    return _send(ctx.obj['wallet'], address, satoshis, use_unconfirmed)


def _send(wallet, address, satoshis, use_unconfirmed=False):
    """Send bitcoin to the specified address"""
    txids = []
    try:
        txids = wallet.send_to(address=address, amount=satoshis, use_unconfirmed=use_unconfirmed)
        # For now there is only a single txn created, so assume it's 0
        txid, txn = txids[0]["txid"], txids[0]["txn"]
        logger.info(uxstring.UxString.send_success.format(satoshis, address, txid, txn))
    except ValueError as e:
        # This will trigger if there's a below dust-limit output.
        raise exceptions.Two1Error(str(e))
    except WalletBalanceError:
        if wallet.unconfirmed_balance() > satoshis:
            raise exceptions.Two1Error(uxstring.UxString.send_insufficient_confirmed)
        else:
            balance = min(wallet.confirmed_balance(), wallet.unconfirmed_balance())
            raise exceptions.Two1Error(uxstring.UxString.send_insufficient_blockchain.format(balance, satoshis, address))
    except DataProviderError as e:
        if "rejected" in str(e):
            raise exceptions.Two1Error(uxstring.UxString.send_rejected)
        else:
            raise exceptions.Two1Error(str(e))
    return txids
