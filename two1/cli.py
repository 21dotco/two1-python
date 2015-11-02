"""
The 21 command line interface.

This command can be invoked as 21, two1, or twentyone. The former is
shorter and easier for use at the CLI; the latter, being alphanumeric,
is preferred within Python or any context where the code needs to be
imported. We have configured setup.py and this code such that the
documentation dynamically updates based on this name.
"""
import sys
import platform

import locale
import os
import sys
import json
import getpass
from codecs import open
from path import path
import click
from path import path
from two1.commands.config import Config
from two1.commands.config import TWO1_CONFIG_FILE
from two1.commands.config import TWO1_VERSION
from two1.lib.server.login import check_setup_twentyone_account
from two1.lib.util.decorators import docstring_parameter
# from two1.commands.update import update_two1_package
from two1.commands.buy import buy
from two1.commands.mine import mine
from two1.commands.log import log
from two1.commands.help import help
from two1.commands.status import status
from two1.commands.update import update
from two1.commands.flush import flush

CLI_NAME = str(path(sys.argv[0]).name)
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--config-file',
              envvar='TWO1_CONFIG_FILE',
              default=TWO1_CONFIG_FILE,
              metavar='PATH',
              help='Path to config (default: %s)' % TWO1_CONFIG_FILE)
@click.option('--config',
              nargs=2,
              multiple=True,
              metavar='KEY VALUE',
              help='Overrides a config key/value pair.')
@click.version_option(TWO1_VERSION, message='%(prog)s v%(version)s')
@click.pass_context
@docstring_parameter(CLI_NAME)
def main(ctx, config_file, config):
    """Buy APIs on the internet for Bitcoin.

\b
Usage
-----
Mine bitcoin at the command line
$ {0} mine

\b
List your new balance
$ {0} status

\b
Buy a search query with Bitcoin
$ {0} buy search "Satoshi Nakamoto"

\b
View an ad-free article with Bitcoin
$ {0} buy content http://on.wsj.com/1IV0HT5

\b
Message someone outside your social network for Bitcoin
$ {0} buy social @balajis "Hi! I'm joe@example.com. My pitch deck: bit.ly/example"

\b
Show this help text
$ {0}

\b
Show help for a command
$ {0} COMMAND --help
"""
    create_wallet_and_account = ctx.invoked_subcommand not in ('help', 'update')
    cfg = Config(config_file, config, create_wallet=create_wallet_and_account)
    if create_wallet_and_account:
        check_setup_twentyone_account(cfg)
        # Disable the auto updater for now.
        # Todo: This needs to be switched on for the prod channel only.
        if cfg.auto_update:
            update_data = update_two1_package(cfg)
            if update_data["update_successful"]:
                # TODO: This should exit the CLI and run the same command using the
                # newly installed software
                pass
    ctx.obj = dict(config=cfg)

main.add_command(buy)
main.add_command(mine)
main.add_command(status)
main.add_command(update)
main.add_command(flush)
main.add_command(log)
main.add_command(help)


if __name__ == "__main__":
    if platform.system() == 'Windows':
        locale.setlocale(locale.LC_ALL, 'us')

    main()
