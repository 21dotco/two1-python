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
    """ View and manage your 21 wallets.

\b
Usage
-----
Each time you log in to a new machine with your 21 account, a new wallet will be created for you.
This command allows you to view and manage all of the wallets associated with your account.
Your account has one primary wallet. The primary wallet is the wallet that your 21 buffer will be flushed
into when you do `21 flush`.

\b
Displays information about all of your wallets.
$ 21 wallet info

\b
Sets the wallet on your current machine as the primary wallet.
$ 21 wallet setprimary

\b
Sets the wallet with the name WALLET_NAME as your primary wallet.
$ 21 wallet setprimary WALLET_NAME

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
Set a primary wallet for your account.

\b
Sets the wallet on your current machine as the primary wallet.
$ 21 wallet setprimary

\b
Sets the wallet with the name WALLET_NAME as your primary wallet.
$ 21 wallet setprimary WALLET_NAME
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
    counter = 1
    logger.info("Wallets\n", fg="yellow")
    for wallet in all_wallets:
        wallet_title = click.style(uxstring.UxString.wallet_title).format(wallet["name"])
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
