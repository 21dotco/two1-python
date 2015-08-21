import os
import sys
import json
import getpass
from codecs import open
from path import path
import click

from two1.debug import dlog
from two1.config import Config
from two1.config import TWO1_CONFIG_FILE
from two1.config import TWO1_VERSION
from two1.config import pass_config
from two1.uxstring import UxString 
from two1.lib.login import check_setup_twentyone_account

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
@click.version_option(TWO1_VERSION)
@click.pass_context
def main(ctx, config_file, config):
    """Buy or sell anything on the internet for Bitcoin.

\b
Examples
--------
Get Bitcoin from the 21.co faucet
$ two1 get

\b
Mine Bitcoin continuously in background (requires a 21 Bitcoin Node; see 21.co)
$ two1 mine

\b
Buy the best English to Spanish translation on the Many Machine Market (MMM)
$ two1 buy en2es --stdin {"text":"Hello"} --sortby rating

\b
Rate the seller after purchase
$ two1 rate example.com/en2es

\b
Sell English-to-Chinese translation by turning your computer into a server
$ two1 sell two1.en2cn --price 1000

\b
Publish your English to Chinese translation service on the Many Machine Market
$ two1 publish two1.en2cn

\b
Show this help text
$ two1

\b
Full documentation: github.com/21dotco/two1"""
    #dlog("two1.main")
    cfg = Config(config_file, config)
    check_setup_twentyone_account(cfg)
    ctx.obj = cfg 

from two1.commands.buy import buy
main.add_command(buy)

from two1.commands.get import get
main.add_command(get)

from two1.commands.mine import mine
main.add_command(mine)

from two1.commands.publish import publish
main.add_command(publish)

from two1.commands.rate import rate
main.add_command(rate)

from two1.commands.search import search
main.add_command(search)

#from two1.commands.sell import sell
#main.add_command(sell)

from two1.commands.status import status
main.add_command(status)
    
if __name__ == "__main__":
    main()

