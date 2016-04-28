""" Two1 command to send bitcoin to another address """
# standart python imports
import base64
import logging

# 3rd party imports
import click
import base58

# two1 imports
from two1.commands.util import decorators
from two1.commands.util import uxstring

# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.group()
def wallet():
    """ View, manage, and configure your 21 wallets.

\b
Usage
-----
Set the current wallet as your master wallet, allowing you to
aggregate information about all wallets from one place.

$ 21 wallet setprimary

$ 21 wallet info
"""
    pass


@wallet.command()
@click.option('-pk', '--public_key', default=None, type=click.STRING,
              help='Specify the wallet public key to set as primary.')
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@decorators.json_output
def setprimary(ctx, public_key):
    """
\b
Sets the current default wallet as the primary wallet for your 21.co account.
$ 21 wallet setprimary

\b
Sets a specific wallet as the primary wallet for your 21.co account.
$ 21 wallet setprimary PUBLIC_KEY

\b
The wallet public keys linked to your 21.co account can be obtained by using
info:
$ 21 wallet info
    """
    return _set_primary_wallet(ctx.obj['client'], public_key)


@wallet.command()
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def info(ctx):
    """
\b
View a list of the wallets associated with your account.
$ 21 wallet info
    """
    return _info(ctx.obj['client'], ctx.obj['machine_auth'])


def _set_primary_wallet(client, public_key):
    # Check if the public_key is encoded properly
    if public_key is not None:
        try:
            public_key = base58.b58decode_check(public_key)
        except ValueError:
            raise click.ClickException(uxstring.UxString.wallet_bad_pubkey.format(
                public_key
            ))

    # client controls the default public_key
    return client.set_primary_wallet(public_key)


def _info(client, machine_auth):
    p = client.list_wallets()

    # get current public key
    cb = machine_auth.public_key.compressed_bytes
    my_public_key = base64.b64encode(cb).decode()

    all_wallets = p.json()
    logger.info("\n")
    counter = 1
    for wallet in all_wallets:
        wallet_title = click.style(uxstring.UxString.wallet_title).format(counter)
        if bool(wallet["is_primary"]):
            wallet_title += uxstring.UxString.primary_wallet_label
        if wallet["public_key"] == my_public_key:
            wallet_title += uxstring.UxString.current_wallet_label

        logger.info(wallet_title)
        lines = [uxstring.UxString.wallet_pub_key.format(wallet["public_key"]),
                 uxstring.UxString.wallet_payout_address.format(wallet["payout_address"])]
        counter += 1
        logger.info("\n".join(lines))

    logger.info("\n")
    logger.info("{} : {}".format(uxstring.UxString.primary_wallet_label,
                                 uxstring.UxString.primary_wallet_desc))
    logger.info("{} : {}".format(uxstring.UxString.current_wallet_label,
                                 uxstring.UxString.current_wallet_desc))
    logger.info("\n")
