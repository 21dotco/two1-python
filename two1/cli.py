import os
import sys
import json
import getpass
import base64
from codecs import open
from path import path
import keyring
import requests
import click

from two1.debug import dlog
from two1.config import Config
from two1.config import TWO1_CONFIG_FILE
from two1.config import TWO1_VERSION
from two1.config import TWO1_HOST
from two1.config import pass_config
from two1.wallet import electrumWallet
from two1.mining import rest_client
from two1.bitcoin.crypto import PrivateKey
from two1.uxstring import UxString 

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
@pass_config
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
    dlog("two1.main")

    ctx.obj = Config(config_file, config)
    first_time_setup(ctx.obj)

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

from two1.commands.sell import sell
main.add_command(sell)

from two1.commands.status import status
main.add_command(status)
    


def first_time_setup(config):
  #check if wallet is ready to use
    #if not config.wallet.is_configured:
    #    #configure wallet with default options
    #    config.wallet.configure(config.wallet.config_options)
    
    #check if mining a/c has been setup
    if not config.mining_auth_pubkey:
        username = create_twentyone_account(config)
        if not username:
            click.echo(UxString.account_failed)
            return False  


def create_twentyone_account(config):
    #mining a/c setup
    #simple key generation
    #TODO: this can be replaced with a process where the user
    #can hit a few random keystrokes to generate a private
    #key
    mining_auth_key = PrivateKey.from_random()
    mining_auth_key_b58 = mining_auth_key.to_b58check()
    #base64 converted public key
    mining_auth_pubkey = base64.b64encode(
                               mining_auth_key.public_key.compressed_bytes)

    #store the username -> private key into the system keychain
    click.echo(UxString.creating_account % config.username)
    mining_rest_client = rest_client.MiningRestClient(mining_auth_key,TWO1_HOST)
    bitcoin_payout_address = config.wallet.current_address()
    click.echo(UxString.payout_address % bitcoin_payout_address)
    try:
        try_username = config.username
        while True:
            if try_username == "" or try_username == None:
                try_username = click.prompt(UxString.enter_username,type=click.STRING)

            r = mining_rest_client.account_post(try_username,bitcoin_payout_address)
            if r.status_code == 200:
                break
            elif r.status_code == 201:
                config.update_key("username",try_username)
                #save the auth keys
                keyring.set_password("system","21dotco_key"+try_username,mining_auth_key_b58)
                config.update_key("mining_auth_pubkey",mining_auth_pubkey)
                config.save()
                break
            elif r.status_code == 400:
                click.echo(UxString.username_exists % try_username)
                try_username = None

        return try_username
        #if r.status_code == 400:
    except requests.exceptions.ConnectionError:
        click.echo(UxString.Error.connection % TWO1_HOST)
    except requests.expcetions.Timeout:
        click.echo(UxString.Error.timeout % TWO1_HOST)



