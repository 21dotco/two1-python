""" Flushes current off-chain balance to the blockchain """
# standard python imports
import logging

# 3rd party importss
import click

# two1 imports
from two1.commands.util import decorators
from two1.commands.util import uxstring
from two1.commands.util import exceptions

# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@decorators.catch_all
@decorators.check_notifications
@decorators.capture_usage
@click.option('-a', '--amount', default=None, type=click.INT,
              help="The amount to be flushed out of your account in Satoshis.")
def flush(ctx, amount):
    """ Flush your 21.co buffer to the blockchain."""
    _flush(ctx.obj['client'], ctx.obj['wallet'], amount)


def _flush(client, wallet, amount=None):
    """ Flushes current off-chain balance to the blockchain

    Args:
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        wallet (two1.wallet.Wallet): a user's wallet instance
        amount (int): The amount to be flushed. Should be more than 10k

    Raises:
        ServerRequestError: if server returns an error code other than 401
    """

    try:
        response = client.flush_earnings(amount=amount)
        if response.ok:
            success_msg = uxstring.UxString.flush_success.format(
                click.style("Flush to Blockchain", fg='magenta'),
                wallet.current_address,
                click.style("21 mine", bold=True))
            logger.info(success_msg)
    except exceptions.ServerRequestError as ex:
        if ex.status_code == 401:
            logger.info(uxstring.UxString.flush_insufficient_earnings)
        elif ex.status_code == 400 and ex.data.get("detail") == "TO500":
            logger.info(uxstring.UxString.flush_not_enough_earnings.format(amount), fg="red")
        else:
            raise ex
