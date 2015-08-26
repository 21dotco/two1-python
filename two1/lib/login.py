import base64

import keyring
import requests
import click
from two1.config import TWO1_HOST
from two1.lib import rest_client
from two1.bitcoin.crypto import PrivateKey
from two1.uxstring import UxString


def check_setup_twentyone_account(config):
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
                          mining_auth_key.public_key.compressed_bytes
                          ).decode()

    #store the username -> private key into the system keychain
    click.echo(UxString.creating_account % config.username)
    mining_rest_client = rest_client.MiningRestClient(mining_auth_key,TWO1_HOST)

    #use the same key for the payout address as well.
    #this will come from the wallet
#    bitcoin_payout_address = config.wallet.current_address()
    bitcoin_payout_address = mining_auth_key.public_key.address()

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
                config.update_key("bitcoin_address",bitcoin_payout_address)
                #save the auth keys
                keyring.set_password("twentyone","mining_auth_key",mining_auth_key_b58)
                config.update_key("mining_auth_pubkey",mining_auth_pubkey)
                
                config.save()
                break
            elif r.status_code == 400:
                click.echo(UxString.username_exists % try_username)
                try_username = None
            else:
                try_username = None

        return try_username
        #if r.status_code == 400:
    except requests.exceptions.ConnectionError:
        click.echo(UxString.Error.connection % TWO1_HOST)
    except requests.expcetions.Timeout:
        click.echo(UxString.Error.timeout % TWO1_HOST)

    return None

