""" Flushes current off-chain balance to the blockchain """
# standard python imports
import base64
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
@click.option('-s', '--silent', is_flag=True, default=False,
              help='Do not show the flush confirmation prompt.')
@click.option('-t', '--to_primary', is_flag=True, default=False,
              help='Flushes to your primary wallet.')
def flush(ctx, amount, denomination, payout_address, silent, to_primary):
    """ Flush your 21.co buffer to the blockchain.

\b
$ 21 flush
Flushes all of your 21.co buffer to your local wallet.

\b
$ 21 flush 30000 satoshis
Flushes 30000 satoshis from your 21.co buffer to your local wallet.
You can use the following denominations: satoshis, bitcoins, and USD.

\b
$ 21 flush 30000 satoshis -p 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa
Flushes 30000 satoshis from your 21.co buffer to the Bitcoin Address 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa .

\b
$ 21 flush --to_primary
Flushes all of your 21.co buffer to your primary wallet. Note that your primary wallet may not be
located on your current computer. You can use the `21 wallet` command to manage your primary wallet.
    """

    amount = currency.convert_amount_to_satoshis_with_prompt(amount, denomination)

    _flush(ctx.obj['client'], ctx.obj['wallet'], ctx.obj['machine_auth'], amount, payout_address,
           silent, to_primary)


def _flush(client, wallet, machine_auth, amount=None, payout_address=None, silent=False,
           to_primary=False):
    """ Flushes current off-chain buffer to the blockchain.

    Args:
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        wallet (two1.wallet.Wallet): a user's wallet instance.
        amount (int): The amount to be flushed. Should be more than 10k.
        payout_address (string): The address to flush the Bitcoins to.
        silent (boolean): If True, disables the confirmation prompt.
        to_primary (boolean): If True, flushes to the primary wallet.

    Raises:
        ServerRequestError: if server returns an error code other than 401.
    """

    # check the payout address
    if payout_address:
        try:
            base58.b58decode_check(payout_address)
        except ValueError:
            logger.error(uxstring.UxString.flush_invalid_address)
            return

    # select the wallet and the associated payout address for the flush
    all_wallets = client.list_wallets()
    wallet_payout_address, wallet_name = _select_flush_wallet(client, machine_auth, payout_address,
                                                              all_wallets, to_primary)

    # ask user for confirmation
    if not silent:
        # if the user has not specified a payout_address then the buffer will be flushed to the
        # primary wallet.
        is_local = payout_address is None
        should_continue = _show_confirmation(machine_auth, amount, all_wallets,
                                             wallet_payout_address, wallet_name, to_primary,
                                             is_local)
        if not should_continue:
            return

    # perform flush
    try:
        response = client.flush_earnings(amount=amount, payout_address=wallet_payout_address)
        if response.ok:
            success_msg = uxstring.UxString.flush_success.format(wallet_payout_address)
            logger.info(success_msg)
    except exceptions.ServerRequestError as ex:
        if ex.status_code == 401:
            logger.info(uxstring.UxString.flush_insufficient_earnings)
        elif ex.status_code == 400 and ex.data.get("detail") == "TO500":
            logger.info(uxstring.UxString.flush_not_enough_earnings.format(amount), fg="red")
        elif ex.status_code == 403 and ex.data.get("error") == "social_account_required_to_flush":
            logger.info("You must connect a social account with your 21.co account before you can flush.", fg="red")
        else:
            raise ex


def _show_confirmation(machine_auth, amount, all_wallets, wallet_payout_address, wallet_name,
                       is_primary, is_local):
    """ Displays a confirmation prompt to the user with information about their flush.

    Args:
        machine_auth (two1.server.MachineAuth): Machine auth object corresponding to the current
        wallet.
        amount (int): The amount to be flushed
        all_wallets (list): List of dictionaries representing all of the user's wallets.
        wallet_payout_address (str): The payout address for the wallet we are flushing into.
        wallet_name (str): The name of the wallet we are flushing into.
        is_primary (boolean): Whether flush is being done to the primary wallet.
        is_local (boolean): whether the user is flushing to to their local wallet.

    Returns (boolean): True if the user decides to continue with flush, False otherwise.
    """
    wallet_payout_address_styled = click.style(wallet_payout_address, bold=True)
    wallet_name_styled = _style_wallet_name(wallet_name, is_primary, is_local)
    amount_styled = _style_amount(amount)

    logger.info(uxstring.UxString.flush_pre_confirmation.format(amount_styled,
                                                                wallet_payout_address_styled,
                                                                wallet_name_styled))

    # if the user is flushing to a wallet not on their computer, show them a warning
    if not _payout_address_belongs_to_current_wallet(wallet_payout_address,
                                                     all_wallets,
                                                     machine_auth):
        logger.info(uxstring.UxString.flushing_to_other_wallet)

    if not click.confirm(uxstring.UxString.flush_confirmation):
        return False

    return True


def _select_flush_wallet(client, machine_auth, payout_address, all_wallets, to_primary):
    """ Selects the wallet name and the associated payout_address for the flush.

    If no payout_address is specified, primary wallet of the user will be used.
    Otherwise all the user's wallets are searched for a matching payout_address.
    If none of the user's wallets match the payout_address the wallet is an external
    wallet and the function returns None.

    Args:
        client (two1.server.rest_client.TwentyOneRestClient): an object for
        sending authenticated requests to the TwentyOne backend.
        machine_auth (two1.server.MachineAuth): Machine auth object corresponding to the current
        wallet.
        payout_address (str): Optionally None string indicating the passed in payout_address
        from the command invocation.
        all_wallets (list): List of dictionaries representing all of the user's wallets.
        to_primary (boolean): Whether flush is being done to the primary wallet.

    Returns:
        payout_address (str): The final payout address that the buffer will be flushed to
        wallet_name (str): The name of the wallet that the buffer will be flushed to.
        If payout_address does not belong to any of the user's wallets, wallet_name is None.
    """

    wallet_name = None

    if to_primary:
        primary_wallet = [w for w in all_wallets if w["is_primary"]][0]
        wallet_payout_address = primary_wallet["payout_address"]
        wallet_name = primary_wallet["name"]

    # if payout_address is None we are flushing to the current wallet
    elif payout_address is None:
        cb = machine_auth.public_key.compressed_bytes
        current_public_key = base64.b64encode(cb).decode()
        current_wallet = [w for w in all_wallets if w["public_key"] == current_public_key][0]
        wallet_payout_address = current_wallet["payout_address"]
        wallet_name = current_wallet["name"]
    else:
        # find a user wallet that is tied to the payout_address
        target_wallet_list = [w for w in all_wallets if w["payout_address"] == payout_address]
        if len(target_wallet_list) > 0:
            target_wallet = target_wallet_list[0]
            wallet_payout_address = target_wallet["payout_address"]
            wallet_name = target_wallet["name"]
        # User is flushing to an external wallet
        else:
            wallet_payout_address = payout_address

    return wallet_payout_address, wallet_name


def _style_amount(amount):
    if amount:
        amount_str = click.style("{} satoshis".format(amount), bold=True)
    else:
        amount_str = click.style("the entire balance", bold=True)

    return amount_str


def _style_wallet_name(wallet_name, is_primary, is_local):
    if wallet_name:
        if is_primary:
            wallet_name_styled = "your primary wallet named " + click.style(wallet_name, bold=True)
        elif is_local:
            wallet_name_styled = "your current local wallet named " + click.style(wallet_name,
                                                                                  bold=True)
        else:
            wallet_name_styled = "your wallet named " + click.style(wallet_name, bold=True)
    else:
        wallet_name_styled = click.style("an external wallet", bold=True)

    return wallet_name_styled


def _payout_address_belongs_to_current_wallet(payout_address, all_wallets, machine_auth):
    """Determines whether payout_address belongs to the current wallet on the user's computer.

    Args:
        payout_address (str): The payout address that the user has specified.
        all_wallets (list): List of dictionaries containing wallet info.
        machine_auth (two1.server.MachineAuth): Machine auth object corresponding to the current
        wallet.

    Returns: True if payout_address belongs to the wallet on the user's current computer.
    """
    target_wallet_list = [w for w in all_wallets if w["payout_address"] == payout_address]
    if len(target_wallet_list) == 0:
        return False
    else:
        target_wallet = target_wallet_list[0]
        cb = machine_auth.public_key.compressed_bytes
        current_public_key = base64.b64encode(cb).decode()
        return target_wallet["public_key"] == current_public_key
