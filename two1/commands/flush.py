""" Flushes current off-chain balance to the blockchain """
# standard python imports
import logging

# 3rd party importss
import base58
import click

# two1 imports
from two1.commands.util import decorators
from two1.commands.util import uxstring
from two1.commands.util import exceptions
from two1.commands.util import currency

# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@decorators.catch_all
@decorators.check_notifications
@decorators.capture_usage
@click.argument('amount', default=0.0, type=click.FLOAT)
@click.argument('denomination', default='', type=click.STRING)
@click.option('-p', '--payout_address', default=None, type=click.STRING,
              help="The Bitcoin address that your 21.co buffer will be flushed to.")
def flush(ctx, amount, denomination, payout_address):
    """ Flush your 21.co buffer to the blockchain.

\b
$ 21 flush
Flushes all of your 21.co buffer to your local wallet.

\b
$ 21 flush 30000 satoshis
Flushes 30000 satoshis from your 21.co buffer to your local wallet.
You can use the following denominations: satoshis, bitcoins, and USD.

\b
$21 flush 30000 satoshis -p 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Flushes 30000 satoshis from your 21.co buffer to the Bitcoin Address 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa .

    """
    if amount != 0.0:
        if denomination == '':
            confirmed = click.confirm(uxstring.UxString.default_price_denomination, default=True)
            if not confirmed:
                raise exceptions.Two1Error(uxstring.UxString.cancel_command)
            denomination = currency.Price.SAT
        amount = currency.Price(amount, denomination).satoshis
    else:
        amount = None
    _flush(ctx.obj['client'], ctx.obj['wallet'], amount, payout_address)


def _flush(client, wallet, amount=None, payout_address=None):
    """ Flushes current off-chain balance to the blockchain

    Args:
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        wallet (two1.wallet.Wallet): a user's wallet instance
        amount (int): The amount to be flushed. Should be more than 10k
        amount (string): The address to flush the Bitcoins to

    Raises:
        ServerRequestError: if server returns an error code other than 401
    """

    if payout_address:
        try:
            # check whether this is a valid Bitcoin address
            base58.b58decode_check(payout_address)
        except ValueError:
            logger.error(uxstring.UxString.flush_invalid_address)
            return
    try:
        response = client.flush_earnings(amount=amount, payout_address=payout_address)
        if response.ok:
            success_msg = uxstring.UxString.flush_success.format(wallet.current_address)
            logger.info(success_msg)
    except exceptions.ServerRequestError as ex:
        if ex.status_code == 401:
            logger.info(uxstring.UxString.flush_insufficient_earnings)
        elif ex.status_code == 400 and ex.data.get("detail") == "TO500":
            logger.info(uxstring.UxString.flush_not_enough_earnings.format(amount), fg="red")
        else:
            raise ex
