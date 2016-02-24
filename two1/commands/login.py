# standard python imports
import sys
import base64

# 3rd party imports
import click

# two1 imports
import two1.lib.server.login as server_login
from two1.lib.blockchain import exceptions

from two1.lib.util.exceptions import TwoOneError, UnloggedException
from two1.lib.util.uxstring import UxString
from two1.lib.wallet import Two1Wallet
from two1.lib.blockchain import TwentyOneProvider
from two1.lib.util.decorators import json_output
from two1.lib.server.analytics import capture_usage
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST, TWO1_PROVIDER_HOST, Config
from two1.lib.wallet.two1_wallet import Wallet
from two1.lib.server.machine_auth_wallet import MachineAuthWallet


@click.command()
@click.option('-sp', '--setpassword', is_flag=True, default=False,
              help='Set/update your 21 password')
@click.option('-u', '--username', default=None, help='The username to login with')
@click.option('-p', '--password', default=None, help='The password to login with')
@json_output
def login(config, setpassword, username, password):
    """Log in to your different 21 accounts."""
    if setpassword:
        return _set_password(config)
    else:
        _login(config, username, password)


@check_notifications
@capture_usage
def _login(config, username, password):
    """ Log in a user into the two1 account

    Args:
        config (Config): config object used for getting .two1 information
        username (str): optional command line arg to skip username prompt
        password (str): optional command line are to skip password prompt
    """
    cfg = Config()
    machine_auth = cfg.machine_auth
    machine_auth_pubkey_b64 = base64.b64encode(machine_auth.public_key.compressed_bytes).decode()
    bitcoin_payout_address = cfg.wallet.current_address
    server_login.signin_account(config=cfg,
                                machine_auth=machine_auth,
                                machine_auth_pubkey_b64=machine_auth_pubkey_b64,
                                bitcoin_payout_address=bitcoin_payout_address,
                                username=username,
                                password=password,
                                show_analytics_prompt=False)


@capture_usage
def _set_password(config):
    """ Upadets the 21 user account password from command line

    Args:
        config (Config): config object used for getting .two1 information
        user (str): name of the user to update password for
    """
    try:
        if not hasattr(config, "username"):
            click.secho(UxString.no_account_found)
            return

        password = server_login.get_password(config.username)
        machine_auth = get_machine_auth(config)
        client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                                 machine_auth,
                                                 config.username)
        client.update_password(password)

    except click.exceptions.Abort:
        pass


def get_machine_auth(config):
    """ Gets the machine auth wallet object from a wallet

    Args:
        config (Config): config object used for getting .two1 information

    Return:
        MachineAuthWallet: machine auth wallet object
    """
    if hasattr(config, "machine_auth"):
        machine_auth = config.machine_auth
    else:
        dp = TwentyOneProvider(TWO1_PROVIDER_HOST)
        wallet_path = Two1Wallet.DEFAULT_WALLET_PATH
        if not Two1Wallet.check_wallet_file(wallet_path):
            create_wallet_and_account()
            return

        wallet = Wallet(wallet_path=wallet_path,
                        data_provider=dp)
        machine_auth = MachineAuthWallet(wallet)

    return machine_auth


def save_config(config, machine_auth, username):
    """
    Todo:
        Merge this function into _login
    """
    machine_auth_pubkey_b64 = base64.b64encode(
        machine_auth.public_key.compressed_bytes
    ).decode()

    click.secho("Logging in {}".format(username), fg="yellow")
    config.load()
    config.update_key("username", username)
    config.update_key("mining_auth_pubkey", machine_auth_pubkey_b64)
    config.save()


def create_wallet_and_account():
    """ Creates a wallet and two1 account

    Raises:
        TwoOneError: if the data provider is unavailable or an error occurs
    """
    try:
        cfg = Config()
        server_login.check_setup_twentyone_account(cfg)
    except exceptions.DataProviderUnavailableError:
        raise TwoOneError(UxString.Error.connection_cli)
    except exceptions.DataProviderError:
        raise TwoOneError(UxString.Error.server_err)
    except UnloggedException:
        sys.exit(1)
