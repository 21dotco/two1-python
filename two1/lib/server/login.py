"""Handles client-side user account setup and authentication."""
import base64
import click
import re

import two1
from two1.cinnabds.util.exceptions import UnloggedException
from two1.lib.server.rest_client import TwentyOneRestClient
from two1.lib.server.rest_client import ServerRequestError
from two1.lib.util.uxstring import UxString


class EmailAddress(click.ParamType):
    """Represents a email address parameter."""
    name = "Email address"

    def __init__(self):
        click.ParamType.__init__(self)

    def convert(self, value, param, ctx):
        if re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
                    value):
            return value
        self.fail(UxString.Error.invalid_email)


class Username(click.ParamType):
    """Represents a username parameter."""
    name = "Username"

    def __init__(self):
        click.ParamType.__init__(self)

    def convert(self, value, param, ctx):
        if re.match(r"^[a-zA-Z][a-zA-Z_0-9]+$", value):
            if len(value) > 4 and len(value) < 32:
                return value
        self.fail(UxString.Error.invalid_username)


class Password(click.ParamType):
    name = "Password"

    def __init__(self):
        click.ParamType.__init__(self)

    def convert(self, value, param, ctx):
        if len(value) < 5:
            self.fail(UxString.short_password)
        if not any(x.isupper() for x in value) or not any(x.islower() for x in value):
            self.fail(UxString.capitalize_password)
        if not any(x.isdigit() for x in value):
            self.fail(UxString.numbers_in_password)

        return value


def get_password(username):
    password = click.prompt(UxString.set_new_password.format(username),
                            hide_input=True, confirmation_prompt=True, type=Password())
    return password


def check_setup_twentyone_account(config):
    """ Checks for a working wallet and a 21 a/c.
    Sets up the a/c and configures a wallet if needed.

    Args:
        config (Config): Config object from the cli
    """
    # check if a/c has been setup with a proper username
    if not config.mining_auth_pubkey:
        username = create_twentyone_account(config)
        if not username:
            click.echo(UxString.account_failed)
            return False


def create_twentyone_account(config):
    """ Attempts to create a 21 a/c using the username that exists
    in the config object.

    Args:
        config (Config): Config object from the cli context.

    Returns:
        str: Returns the username that was created, None otherwise
    """
    create_username(config)
    return config.username


def create_username(config, username=None):
    """ Creates a private auth key and associates it with a 21 account.
    If the username already exists, it prompts the user for the new username.
    The private key is saved in system default keyring. The config is updated
    and saved with the username and the base64 encoded public key.

    Args:
        config (Config):  Config object from the cli context.
        username (str): Attempt to create the user with this username.

    Returns:
        str: The username that the a/c was created with.
    """
    # twentyone a/c setup
    # simple key generation
    # TODO: this can be replaced with a process where the user
    # can hit a few random keystrokes to generate a private
    # key
    # check if a key already exists and use it

    click.echo(UxString.missing_account)
    machine_auth = config.machine_auth
    if not machine_auth:
        raise ValueError("Error: Auth is not initialized.")
    # get public key and convert to base64 for storage
    machine_auth_pubkey_b64 = base64.b64encode(
        machine_auth.public_key.compressed_bytes
    ).decode()
    # use the same key for the payout address as well.
    # this will come from the wallet
    bitcoin_payout_address = config.wallet.current_address
    click.echo("")

    # if the user is on a bitcoin computer create the account for them
    # otherwise login
    if TWO1_DEVICE_ID:
        return _create_account(config, username, machine_auth, machine_auth_pubkey_b64,
                               bitcoin_payout_address)
    else:
        return signin_account(config, machine_auth, machine_auth_pubkey_b64,
                               bitcoin_payout_address)


def _create_account(config, username, machine_auth, machine_auth_pubkey_b64,
                    bitcoin_payout_address):

    click.echo(UxString.missing_account)
    email = click.prompt(UxString.enter_email, type=EmailAddress())
    while True:
        if username == "" or username is None:
            click.echo("")
            username = click.prompt(UxString.enter_username, type=Username())
            click.echo("")
            click.echo(UxString.creating_account % username)
            password = get_password(username)

        rest_client = TwentyOneRestClient(two1.TWO1_HOST, machine_auth, username)
        try:
            r = rest_client.account_post(bitcoin_payout_address, email, password)
            click.echo(UxString.payout_address % bitcoin_payout_address)
            config.set("username", username)
            config.set("mining_auth_pubkey", machine_auth_pubkey_b64)
            # Ask for opt-in to analytics
            analytics_optin(config)
            break
        except ServerRequestError as e:
            if e.status_code == 400:
                click.echo(UxString.username_exists % username)
            elif e.status_code == 404:
                click.echo(UxString.Error.invalid_username)
            elif e.status_code == 403:
                r = e.data
                if "detail" in r and "TO200" in r["detail"]:
                    click.secho(UxString.max_accounts_reached)
                raise UnloggedException("Bitcoin Computer Needed")
            else:
                click.echo(UxString.Error.account_failed)
            username = None
    return username


def signin_account(config, machine_auth, machine_auth_pubkey_b64, bitcoin_payout_address,
                   username=None, password=None, show_analytics_prompt=True):
    click.secho(UxString.signin_title)
    username = username or get_username_interactive()
    password = password or get_password_interactive()
    login_with_username_password(config, username, password, machine_auth,
                                            bitcoin_payout_address)

    click.echo(UxString.payout_address % bitcoin_payout_address)
    config.update_key("username", username)
    config.update_key("mining_auth_pubkey", machine_auth_pubkey_b64)
    config.save()
    if show_analytics_prompt:
        analytics_optin(config)
    return username


def login_with_username_password(config, username, password, machine_auth, payout_address):
    click.secho(UxString.login_in_progress.format(username))
    rest_client = TwentyOneRestClient(two1.TWO1_HOST, machine_auth=machine_auth, username=username)
    try:
        r = rest_client.login(payout_address=payout_address, password=password)
    except ServerRequestError as e:
        if e.status_code == 401:
            click.secho(UxString.incorrect_password)
            raise UnloggedException("Unauthorized Login")
        else:
            click.secho("Error: " + str(next(iter(e.data.values()))) + "({})".format(e.status_code),
                        fg="red")
            raise UnloggedException(e)


def get_username_interactive():
    username = click.prompt(UxString.login_username, type=str)
    return username


def get_password_interactive():
    password = click.prompt(UxString.login_password, hide_input=True, type=str)
    return password



def analytics_optin(config):
    """ Set the collect_analytics flag to enable analytics collection.
    Args:
        config: Config object from the cli context.
    """
    if click.confirm(UxString.analytics_optin):
        config.set("collect_analytics", True)
        click.echo(UxString.analytics_thankyou)
    else:
        click.echo("")
