"""
The 21 command line interface.

This command can be invoked as 21 or two1. The former is shorter and
easier for use at the command line; the latter name (two1) begins with
a letter and is thus preferred within Python or any context where 21
is imported as library.
"""
import platform
import locale
import click
import logging

import two1
import two1.commands.util.logger

from two1.commands.util import bitcoin_computer
from two1.server import rest_client
from two1.server import machine_auth_wallet
from two1.commands.util import config as two1_config
from two1.commands.util import uxstring
from two1.commands.util import decorators
from two1.commands.util import exceptions
from two1.commands.util import wallet as wallet_utils
from two1.commands.util import account as account_utils
from two1.commands.buy import buy
from two1.commands.buybitcoin import buybitcoin
from two1.commands.doctor import doctor
from two1.commands.mine import mine
from two1.commands.log import log
from two1.commands.inbox import inbox
from two1.commands.login import login
from two1.commands.help import help
from two1.commands.status import status
from two1.commands.update import update
from two1.commands.uninstall import uninstall
from two1.commands.flush import flush
from two1.commands.send import send
from two1.commands.search import search
from two1.commands.rate import rate
from two1.commands.publish import publish
from two1.commands.profile import profile
from two1.commands.join import join
from two1.commands.sell import sell
from two1.commands.earn import earn
from two1.commands.faucet import faucet


logger = logging.getLogger(__name__)

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


def parse_config(config_file=two1.TWO1_CONFIG_FILE,
                 config_dict=None,
                 need_wallet_and_account=True):
    """Get configuration information that is used to drive all 21 commands.

    This function is very useful for testing as it builds up several
    key variables (like the client, wallet, username, and the like)
    that are used in many commands. The way it does this is by taking
    in the config_file (typically .two1/two1.json) and the config_dict
    (a list of key-value pairs to override the config_file, typically
    an empty dictionary), and then running the logic below.

    It returns obj which is a dictionary that has Config, Wallet,
    MachineAuth, and TwentyOneRestClient instances underneath it, as
    well as a string with the username. The obj is passed down by
    click to various other commands.

    You can use this function in any test to instantiate the user's
    wallet, username, and other variables.
    """
    try:
        config = two1_config.Config(config_file, config_dict)
    except exceptions.FileDecodeError as e:
        raise click.ClickException(uxstring.UxString.Error.file_decode.format((str(e))))

    wallet, machine_auth, username, client = None, None, None, None
    if need_wallet_and_account:
        wallet = wallet_utils.get_or_create_wallet(config.wallet_path)
        machine_auth = machine_auth_wallet.MachineAuthWallet(wallet)
        username = account_utils.get_or_create_username(config, machine_auth)
        client = rest_client.TwentyOneRestClient(two1.TWO1_HOST, machine_auth, config.username)
        config.username = username

    obj = dict(config=config,
               wallet=wallet,
               machine_auth=machine_auth,
               username=username,
               client=client)
    return obj


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--config-file',
              envvar='TWO1_CONFIG_FILE',
              default=two1.TWO1_CONFIG_FILE,
              metavar='PATH',
              help='Path to config (default: %s)' % two1.TWO1_CONFIG_FILE)
@click.option('--config', 'config_pairs',
              nargs=2,
              multiple=True,
              metavar='KEY VALUE',
              help='Overrides a config key/value pair.')
@click.version_option(two1.TWO1_VERSION, message='%(prog)s v%(version)s')
@click.pass_context
@decorators.catch_all
def main(ctx, config_file, config_pairs):
    """Buy and sell anything on the internet for bitcoin.

\b
For detailed help, run 21 help --detail.
For full documentation, visit 21.co/learn.
"""
    need_wallet_and_account = ctx.invoked_subcommand not in (
        'help', 'update', 'login', 'doctor')

    # Set UUID if available
    uuid = bitcoin_computer.get_device_uuid()
    if uuid:
        two1.TWO1_DEVICE_ID = uuid

    ctx.obj = parse_config(config_file,
                           dict(config_pairs),
                           need_wallet_and_account=need_wallet_and_account)


main.add_command(buy)
main.add_command(buybitcoin)
main.add_command(doctor)
if bitcoin_computer.has_mining_chip():
    main.add_command(mine)
main.add_command(status)
main.add_command(update)
main.add_command(uninstall)
main.add_command(flush)
main.add_command(log)
main.add_command(help)
main.add_command(send)
main.add_command(search)
main.add_command(rate)
main.add_command(inbox)
main.add_command(sell)
main.add_command(publish)
main.add_command(login)
main.add_command(profile)
main.add_command(join)
main.add_command(earn)
main.add_command(faucet)

if __name__ == "__main__":
    if platform.system() == 'Windows':
        locale.setlocale(locale.LC_ALL, 'us')
    main()
