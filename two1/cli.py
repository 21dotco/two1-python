"""
The 21 command line interface.

This command can be invoked as 21, two1, or twentyone. The former is
shorter and easier for use at the CLI; the latter, being alphanumeric,
is preferred within Python or any context where the code needs to be
imported. We have configured setup.py and this code such that the
documentation dynamically updates based on this name.
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
from two1.commands.flush import flush
from two1.commands.send import send
from two1.commands.search import search
from two1.commands.rate import rate
from two1.commands.publish import publish
from two1.commands.join import join
from two1.commands.sell import sell


logger = logging.getLogger(__name__)

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--config-file',
              envvar='TWO1_CONFIG_FILE',
              default=two1.TWO1_CONFIG_FILE,
              metavar='PATH',
              help='Path to config (default: %s)' % two1.TWO1_CONFIG_FILE)
@click.option('--config', 'config_dict',
              nargs=2,
              multiple=True,
              metavar='KEY VALUE',
              help='Overrides a config key/value pair.')
@click.version_option(two1.TWO1_VERSION, message='%(prog)s v%(version)s')
@click.pass_context
@decorators.catch_all
def main(ctx, config_file, config_dict):
    """Mine bitcoin and use it to buy and sell digital goods.

\b
Usage
-----
Mine bitcoin, list your balance, and buy a search query without ads.
$ 21 mine
$ 21 status

\b
For further details on how you can use your mined bitcoin to buy digital
goods both at the command line and programmatically, visit 21.co/learn
"""
    need_wallet_and_account = ctx.invoked_subcommand not in ('help', 'update', 'login')

    # sets UUID if avaliable
    uuid = bitcoin_computer.get_device_uuid()
    if uuid:
        two1.TWO1_DEVICE_ID = uuid

    try:
        config = two1_config.Config(config_file, config_dict)
        ctx.obj = dict(config=config, client=None, wallet=None)
    except exceptions.FileDecodeError as e:
        raise click.ClickException(uxstring.UxString.Error.file_decode.format((str(e))))

    if need_wallet_and_account:
        ctx.obj['wallet'] = wallet_utils.get_or_create_wallet(config.wallet_path)
        ctx.obj['machine_auth'] = machine_auth_wallet.MachineAuthWallet(ctx.obj['wallet'])
        config.username = account_utils.get_or_create_username(config, ctx.obj['machine_auth'])
        ctx.obj['client'] = rest_client.TwentyOneRestClient(two1.TWO1_HOST, ctx.obj['machine_auth'], config.username)


main.add_command(buy)
main.add_command(buybitcoin)
main.add_command(doctor)
main.add_command(mine)
main.add_command(status)
main.add_command(update)
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
main.add_command(join)

if __name__ == "__main__":
    if platform.system() == 'Windows':
        locale.setlocale(locale.LC_ALL, 'us')

    main()
