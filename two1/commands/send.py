# 3rd party imports
import click

# two1 imports
from two1.lib.blockchain.exceptions import DataProviderError
from two1.lib.wallet.exceptions import WalletBalanceError
from two1.commands.util import decorators
from two1.commands.util import uxstring


@click.command("send")
@click.argument('address', type=click.STRING)
@click.argument('satoshis', type=click.INT)
@click.option('--use-unconfirmed', '-u',
              is_flag=True,
              default=False,
              show_default=True,
              help="Use unconfirmed transactions/UTXOs")
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
    _send(ctx.obj['wallet'], address, satoshis, use_unconfirmed)


def _send(wallet, address, satoshis, use_unconfirmed=False):
    """Send bitcoin to the specified address"""
    txids = []
    try:
        txids = wallet.send_to(address=address, amount=satoshis, use_unconfirmed=use_unconfirmed)
        # For now there is only a single txn created, so assume it's 0
        txid, txn = txids[0]["txid"], txids[0]["txn"]
        click.echo(uxstring.UxString.send_success.format(satoshis, address, txid, txn))
    except ValueError as e:
        # This will trigger if there's a below dust-limit output.
        raise click.ClickException(str(e))
    except WalletBalanceError:
        if wallet.unconfirmed_balance() > satoshis:
            raise click.ClickException(uxstring.UxString.send_insufficient_confirmed)
        else:
            balance = min(wallet.confirmed_balance(), wallet.unconfirmed_balance())
            raise click.ClickException(send_insufficient_blockchain.format(balance, satoshis, address))
    except DataProviderError as e:
        if "rejected" in str(e):
            raise click.ClickException(uxstring.UxString.send_rejected)
        else:
            raise click.ClickException(str(e))
    return txids
