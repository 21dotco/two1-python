# 3rd party imports
import click

# two1 imports
from two1.lib.blockchain.exceptions import DataProviderError
from two1.lib.wallet.exceptions import WalletBalanceError
from two1.lib.util.decorators import json_output


@click.command("send")
@click.argument('address', type=click.STRING)
@click.argument('satoshis', type=click.INT)
@click.option('--use-unconfirmed', '-u',
              is_flag=True,
              default=False,
              show_default=True,
              help="Use unconfirmed transactions/UTXOs")
@json_output
def send(config, address, satoshis, use_unconfirmed):
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
    w = config.wallet
    balance = min(w.confirmed_balance(),
                  w.unconfirmed_balance())
    try:
        txids = w.send_to(address=address,
                          amount=satoshis,
                          use_unconfirmed=use_unconfirmed)
        # For now there is only a single txn created, so assume it's 0
        txid = txids[0]["txid"]
        tx = txids[0]["txn"]
        click.echo("Successfully sent %s satoshis to %s.\n"
                   "txid: %s\n"
                   "tx: %s\n"
                   "To see in the blockchain: "
                   "https://blockexplorer.com/tx/%s\n"
                   % (satoshis, address, txid, tx, txid))
    except ValueError as e:
        # This will trigger if there's a below dust-limit output.
        raise click.ClickException(str(e))
    except WalletBalanceError:
        if w.unconfirmed_balance() > satoshis:
            raise click.ClickException("Insufficient confirmed balance. However, you can use"
                                       "unconfirmed transactions using --use-unconfirmed.")
        else:
            raise click.ClickException("Insufficient Blockchain balance of %s satoshis.\n"
                                       "Cannot send %s satoshis to %s.\n"
                                       "Do %s, then %s to increase your Blockchain balance." %
                                       (balance, satoshis, address,
                                        click.style("21 mine", bold=True),
                                        click.style("21 flush", bold=True)))
        txids = []
    except DataProviderError as e:
        if "rejected" in str(e):
            raise click.ClickException("Transaction rejected.\n"
                                       "You may have to wait for other transactions to confirm.\n")
        else:
            raise click.ClickException(str(e))
    return txids
