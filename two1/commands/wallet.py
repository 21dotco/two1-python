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


@click.command("wallet")
@click.option('--set_primary', '-sp',
              default=None, type=click.STRING,
              help="Set a wallet as your primary wallet.")
@click.option('--info', '-l',
              is_flag=True,
              default=False,
              show_default=True,
              help="List all wallets associated with your 21 account.")
@decorators.catch_all
@decorators.json_output
def wallet(ctx, set_primary, info):
    """ View, manage, and configure your 21 wallets.

\b
Usage
-----
Set the current wallet as your master wallet, allowing you to
aggregate information about all wallets from one place.

$ 21 wallet --set_primary
$ 21 wallet --info
"""
    if set_primary:
        return _set_primary_wallet(ctx.obj['client'], set_primary)
    elif info:
        return _info(ctx.obj['client'], ctx.obj['machine_auth'])
    else:
        logger.info(ctx.command.help)


def _set_primary_wallet(client, public_key):
    # Check if the public_key is encoded properly
    if public_key is not None:
        try:
            public_key = base58.b58decode_check(public_key)
        except ValueError:
            click.ClickException(uxstring.UxString.wallet_bad_pubkey.format(
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
    logger.info(uxstring.UxString.wallet_top_title)
    counter = 1
    for wallet in all_wallets:
        wallet_title = click.style(uxstring.UxString.wallet_title).format(counter)
        if bool(wallet["is_primary"]):
            wallet_title += click.style(" [Primary Wallet]", fg="green")
        if wallet["public_key"] == my_public_key:
            wallet_title += click.style(" [Current Wallet]", fg="magenta")

        logger.info(wallet_title)
        lines = [uxstring.UxString.wallet_pub_key.format(wallet["public_key"]),
                 uxstring.UxString.wallet_payout_address.format(wallet["payout_address"])]
        counter += 1
        logger.info("\n".join(lines))

