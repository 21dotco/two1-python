import base64
import click
import sys
from two1.lib.server.login import check_setup_twentyone_account

from two1.lib.blockchain.exceptions import DataProviderUnavailableError, DataProviderError
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
import two1.lib.server.login as server_login


@click.command()
@json_output
def login(config):
    """login into your different 21 accounts"""
    return _login(config)


@capture_usage
def _login(config):
    if config.username:
        click.secho("currently logged in as: {}".format(config.username), fg="blue")

    # get machine auth
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

    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             machine_auth)

    # get a list of all usernames for device_id/wallet_pk pair
    res = client.account_info()
    usernames = res.json()["usernames"]
    if len(usernames) == 0:
        create_wallet_and_account()
        return


    else:
        # interactively select the username
        counter = 1
        click.secho(UxString.registered_usernames_title)
        for user in usernames:
            click.secho("{}- {}".format(counter, user))
            counter += 1

        username_index = -1
        while username_index <= 0 or username_index > len(usernames):
            username_index = click.prompt(UxString.login_prompt, type=int)
            if username_index <= 0 or username_index > len(usernames):
                click.secho(UxString.login_prompt_invalid_user.format(1, len(usernames)))

        username = usernames[username_index - 1]

        # save the selection in the config file
        save_config(config, machine_auth, username)


def save_config(config, machine_auth, username):
    machine_auth_pubkey_b64 = base64.b64encode(
        machine_auth.public_key.compressed_bytes
    ).decode()

    click.secho("Logging in {}".format(username), fg="yellow")
    config.load()
    config.update_key("username", username)
    config.update_key("mining_auth_pubkey", machine_auth_pubkey_b64)
    config.save()


def create_wallet_and_account():
    try:
        cfg = Config()
        check_setup_twentyone_account(cfg)
    except DataProviderUnavailableError:
        raise TwoOneError(UxString.Error.connection_cli)
    except DataProviderError:
        raise TwoOneError(UxString.Error.server_err)
    except UnloggedException:
        sys.exit(1)
