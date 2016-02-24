# standard python imports
import sys
import base64

# 3rd party imports
import click

# two1 imports
import two1
import two1.lib.server.login as server_login
from two1.lib.blockchain import exceptions
from two1.commands.util.exceptions import TwoOneError, UnloggedException
from two1.commands.util.uxstring import UxString
from two1.lib.wallet import Two1Wallet
from two1.lib.blockchain import TwentyOneProvider
from two1.commands.util import decorators
from two1.lib.server import analytics
from two1.lib.server import rest_client
from two1.lib.wallet.two1_wallet import Wallet
from two1.lib.server.machine_auth_wallet import MachineAuthWallet


@click.command()
@click.option('-sp', '--setpassword', is_flag=True, default=False,
              help='Set/update your 21 password')
@click.option('-u', '--username', default=None, help='The username to login with')
@click.option('-p', '--password', default=None, help='The password to login with')
@decorators.json_output
@analytics.capture_usage
def login(ctx, setpassword, username, password):
    """Log in to your 21 account.

\b
Usage
_____
Use an interactive login prompt to log in to your 21 account.
$ 21 login

\b
Log in without the login prompt.
$ 21 login -u your_username -p your_password

\b
Change the password for the currently logged in user.
$ 21 login -sp

\b
View the user that is currently logged in.
$ 21 login -a
    """
    if setpassword:
        return _set_password(ctx.obj['config'], ctx.obj['client'])
    else:
        _login(ctx.obj['config'], ctx.obj['wallet'], username, password)


@check_notifications
@capture_usage
def _login(config, wallet, username, password):
    """ Log in a user into the two1 account

    Args:
        config (Config): config object used for getting .two1 information
        username (str): optional command line arg to skip username prompt
        password (str): optional command line are to skip password prompt
    """
    machine_auth = config.machine_auth
    machine_auth_pubkey_b64 = base64.b64encode(machine_auth.public_key.compressed_bytes).decode()
    bitcoin_payout_address = wallet.current_address
    server_login.signin_account(config=config,
                                machine_auth=machine_auth,
                                machine_auth_pubkey_b64=machine_auth_pubkey_b64,
                                bitcoin_payout_address=bitcoin_payout_address,
                                username=username,
                                password=password,
                                show_analytics_prompt=False)


@capture_usage
def _set_password(config, client):
    """ Upadets the 21 user account password from command line

    Args:
        config (Config): config object used for getting .two1 information
        client (two1.lib.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
    """
    try:
        if not hasattr(config, "username"):
            click.secho(UxString.no_account_found)
            return

        password = server_login.get_password(config.username)
        machine_auth = get_machine_auth(config)
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
        dp = TwentyOneProvider(two1.TWO1_PROVIDER_HOST)
        wallet_path = Two1Wallet.DEFAULT_WALLET_PATH
        if not Two1Wallet.check_wallet_file(wallet_path):
            create_wallet_and_account(config)
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


def create_wallet_and_account(config):
    """ Creates a wallet and two1 account

    Raises:
        TwoOneError: if the data provider is unavailable or an error occurs
    """
    try:
        server_login.check_setup_twentyone_account(config)
    except exceptions.DataProviderUnavailableError:
        raise TwoOneError(UxString.Error.connection_cli)
    except exceptions.DataProviderError:
        raise TwoOneError(UxString.Error.server_err)
    except UnloggedException:
        sys.exit(1)
