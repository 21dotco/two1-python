""" Two1 command to send bitcoin to another address """
# standart python imports
import base64
import logging

# 3rd party imports
import click

# two1 imports
from two1.commands.util import decorators
from two1.commands.util import uxstring

# Creates a ClickLogger
from two1.commands.util.exceptions import ServerRequestError

logger = logging.getLogger(__name__)


@click.group()
def wallet():
    """ View and manage your 21 wallets.

\b
Usage
-----
Each time you log in to a new machine with your 21 account, a new wallet will be created for you.
This command allows you to view and manage all of the wallets associated with your account.
Your account has one primary wallet. You can use `21 flush -t` to flush your buffer to your primary wallet.

\b
Displays information about all of your wallets.
$ 21 wallet info

\b
Sets the wallet on your current machine as the primary wallet.
$ 21 wallet setprimary

\b
Sets the wallet with the name WALLET_NAME as your primary wallet.
$ 21 wallet setprimary --name WALLET_NAME

"""
    pass


@wallet.command()
@click.option('-n', '--name', default=None, type=click.STRING,
              help='Name of the wallet to set as the primary wallet.')
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@decorators.json_output
def setprimary(ctx, name):
    """
Set a primary wallet for your account.

\b
Sets the wallet on your current machine as the primary wallet.
$ 21 wallet setprimary

\b
Sets the wallet with the name WALLET_NAME as your primary wallet.
$ 21 wallet setprimary --name WALLET_NAME
    """
    return _set_primary_wallet(ctx.obj['client'], name)


@wallet.command()
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@decorators.json_output
def info(ctx):
    """
\b
View a list of the wallets associated with your account.
    """
    return _info(ctx.obj['client'], ctx.obj['machine_auth'])


def _set_primary_wallet(client, name):
    # Check if the public_key is encoded properly
    # client controls the default public_key
    try:
        primary_wallet_info = client.set_primary_wallet(name)
    except ServerRequestError as e:
        if e.status_code == 404:
            logger.info(uxstring.UxString.wallet_name_not_found.format(name), fg="red")
            return {'name': name, 'success': False}

    primary_wallet_name = primary_wallet_info["primary_wallet_name"]
    logger.info(uxstring.UxString.set_primary_wallet_success.format(primary_wallet_name),
                fg="green")
    return {'name': name, 'success': True}


def _info(client, machine_auth):
    all_wallets = client.list_wallets()

    # get current public key
    cb = machine_auth.public_key.compressed_bytes
    my_public_key = base64.b64encode(cb).decode()

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
        logger.info("\n".join(lines))

    logger.info("\n")
    logger.info("{} : {}".format(uxstring.UxString.primary_wallet_label,
                                 uxstring.UxString.primary_wallet_desc))
    logger.info("{} : {}".format(uxstring.UxString.current_wallet_label,
                                 uxstring.UxString.current_wallet_desc))
    logger.info("\n")

    return all_wallets
