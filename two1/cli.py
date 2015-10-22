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
from two1.commands.update import update_two1_package
from two1.commands.buy import buy
from two1.commands.mine import mine
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
    """Buy or sell anything on the internet for Bitcoin.

\b
Examples
--------
Mine Bitcoin at the command line
$ {0} mine

\b
Search for Bitcoin-payable APIs to translate English to Spanish
$ {0} search en2es

\b
Buy the lowest priced English to Spanish translation for Bitcoin
$ {0} buy en2es --sortby price --stdin "Hello World"

\b
Rate the seller after your purchase
$ {0} rate example.com/en2es

\b
Sell translation at 1000 Satoshis-per-word with the 21 micropayments server
$ {0} sell twentyone.es2en --price 1000

\b
Publish your new translation service so that others can buy
$ {0} publish twentyone.en2es

\b
Show this help text
$ {0}
"""
    cfg = Config(config_file, config)
    check_setup_twentyone_account(cfg)
    # Disable the auto updater for now.
    # Todo: This needs to be switched on for the prod channel only.
    if cfg.auto_update:
        update_data = update_two1_package(cfg)
        if update_data["update_successful"]:
            # TODO: This should exit the CLI and run the same command using the
            # newly installed software
            pass
    ctx.obj = cfg

main.add_command(buy)
main.add_command(mine)
main.add_command(status)
main.add_command(update)
main.add_command(flush)


if __name__ == "__main__":
    if platform.system() == 'Windows':
        locale.setlocale(locale.LC_ALL, 'us')

    main()
