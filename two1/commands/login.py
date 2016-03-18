# standard python imports
import sys
import base64
import re
import logging

# 3rd party imports
import click

# two1 imports
import two1
from two1.blockchain import exceptions as blockchain_exceptions
from two1.commands.util import exceptions
from two1.commands.util import uxstring
from two1.commands.util import decorators
from two1.commands.util import wallet as wallet_util
from two1.lib.server import rest_client as _rest_client
from two1.lib.wallet import two1_wallet
from two1.lib.server import machine_auth_wallet


# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.option('-sp', '--setpassword', is_flag=True, default=False,
              help='Set/update your 21 password')
@click.option('-u', '--username', default=None, help='The username to login with')
@click.option('-p', '--password', default=None, help='The password to login with')
@decorators.catch_all
@decorators.json_output
@decorators.capture_usage
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

    """
    config = ctx.obj['config']

    # A user needs to have a machine auth wallet in order to login to anything
    wallet = wallet_util.get_or_create_wallet(config, config.wallet_path)
    machine_auth = machine_auth_wallet.MachineAuthWallet(wallet)

    if setpassword:
        return set_password(config, machine_auth)
    else:
        return login_account(config, machine_auth, username, password)


def login_account(config, machine_auth, username=None, password=None):
    """ Log in a user into the two1 account

    Args:
        config (Config): config object used for getting .two1 information
        username (str): optional command line arg to skip username prompt
        password (str): optional command line are to skip password prompt
    """
    # prints the sign up page link
    logger.info(uxstring.UxString.signin_title)

    # uses specifies username or asks for a different one
    username = username or get_username_interactive()
    password = password or get_password_interactive()

    # use existing username in config
    rest_client = _rest_client.TwentyOneRestClient(two1.TWO1_HOST, machine_auth, username)

    # get the payout address and the pubkey from the machine auth wallet
    machine_auth_pubkey_b64 = base64.b64encode(machine_auth.public_key.compressed_bytes).decode()
    payout_address = machine_auth.wallet.current_address

    logger.info(uxstring.UxString.login_in_progress.format(username))
    try:
        _ = rest_client.login(payout_address=payout_address, password=password)
    # handles 401 gracefully
    except exceptions.ServerRequestError as ex:
        if ex.status_code == 401:
            raise exceptions.UnloggedException(uxstring.UxString.incorrect_password)
        elif ex.status_code == 403 and "error" in ex.data and ex.data["error"] == "TO408":
            email = ex.data["email"]
            raise exceptions.UnloggedException(click.style(uxstring.UxString.unconfirmed_email.format(email),
                                                           fg="blue"))
        else:
            raise ex

    logger.info(uxstring.UxString.payout_address % payout_address)

    # Save the new username and auth key
    config.set("username", username)
    config.set("mining_auth_pubkey", machine_auth_pubkey_b64)
    config.save()

    # Ask for opt-in to analytics
    analytics_optin(config)


def create_account_on_bc(config, machine_auth):
    """ Creates an account for the current machine auth wallet

    Args:
        config (Config): config object used for getting .two1 information
        machine_auth (MachineAuthWallet): machine auth wallet used for authentication
    """
    # get the payout address and the pubkey from the machine auth wallet
    machine_auth_pubkey_b64 = base64.b64encode(machine_auth.public_key.compressed_bytes).decode()
    payout_address = machine_auth.wallet.current_address

    logger.info(uxstring.UxString.missing_account)
    email = None
    username = None
    while True:
        if not email:
            email = click.prompt(uxstring.UxString.enter_email, type=EmailAddress())

        # prompts for a username and password
        if not username:
            try:
                logger.info("")
                username = click.prompt(uxstring.UxString.enter_username, type=Username())
                logger.info("")
                logger.info(uxstring.UxString.creating_account % username)
                password = click.prompt(uxstring.UxString.set_new_password.format(username),
                                        hide_input=True, confirmation_prompt=True, type=Password())
            except click.Abort:
                return

        try:
            # change the username of the given username
            rest_client = _rest_client.TwentyOneRestClient(two1.TWO1_HOST, machine_auth, username)
            rest_client.account_post(payout_address, email, password)

        # Do not continue creating an account because the UUID is invalid
        except exceptions.BitcoinComputerNeededError:
            raise

        except exceptions.ServerRequestError as ex:
            # handle various 400 errors from the server
            if ex.status_code == 400:
                if "error" in ex.data:
                    error_code = ex.data["error"]
                    # email exists
                    if error_code == "TO401":
                        logger.info(uxstring.UxString.email_exists.format(email))
                        email = None
                        continue
                    # username exists
                    elif error_code == "TO402":
                        logger.info(uxstring.UxString.username_exists % username)
                        username = None
                        continue
                # unexpected 400 error
                else:
                    raise exceptions.Two1Error(
                        str(next(iter(ex.data.values()), "")) + "({})".format(ex.status_code))

            # handle an invalid username format
            elif ex.status_code == 404:
                logger.info(uxstring.UxString.Error.invalid_username)
            # handle an error where a bitcoin computer is necessary
            elif ex.status_code == 403:
                r = ex.data
                if "detail" in r and "TO200" in r["detail"]:
                    raise exceptions.UnloggedException(uxstring.UxString.max_accounts_reached)
            else:
                logger.info(uxstring.UxString.Error.account_failed)
            username = None

        # created account successfully
        else:
            logger.info(uxstring.UxString.payout_address % payout_address)

            # save new username and password
            config.set("username", username)
            config.set("mining_auth_pubkey", machine_auth_pubkey_b64)
            config.save()

            # Ask for opt-in to analytics
            analytics_optin(config)

            break


def analytics_optin(config):
    """ Set the collect_analytics flag to enable analytics collection.
    Args:
        config: Config object from the cli context.
    """
    if click.confirm(uxstring.UxString.analytics_optin):
        config.set("collect_analytics", True, should_save=True)
        logger.info(uxstring.UxString.analytics_thankyou)
    else:
        logger.info("")


def get_username_interactive():
    """ Prompts the user for a username using click.prompt """
    username = click.prompt(uxstring.UxString.login_username, type=str)
    return username


def get_password_interactive():
    """ Prompts the user for a password using click.prompt """
    password = click.prompt(uxstring.UxString.login_password, hide_input=True, type=str)
    return password


def set_password(config, machine_auth):
    """ Upadets the 21 user account password from command line

    Args:
        config (Config): config object used for getting .two1 information
        client (two1.lib.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
    """
    if not config.username:
        logger.info(uxstring.UxString.login_required)
        return

    # use existing username in config
    rest_client = _rest_client.TwentyOneRestClient(two1.TWO1_HOST, machine_auth, config.username)

    try:
        password = click.prompt(uxstring.UxString.set_new_password.format(config.username),
                                hide_input=True, confirmation_prompt=True, type=Password())
        rest_client.update_password(password)
    except click.exceptions.Abort:
        pass


class Password(click.ParamType):
    """ Param validator class for prompting user for password """
    name = "Password"

    def __init__(self):
        click.ParamType.__init__(self)

    def convert(self, value, param, ctx):
        if len(value) < 5:
            self.fail(uxstring.UxString.short_password)
        if not any(x.isupper() for x in value) or not any(x.islower() for x in value):
            self.fail(uxstring.UxString.capitalize_password)
        if not any(x.isdigit() for x in value):
            self.fail(uxstring.UxString.numbers_in_password)

        return value


class EmailAddress(click.ParamType):
    """ Param validator class for prompting user for email address"""
    name = "Email address"

    def __init__(self):
        click.ParamType.__init__(self)

    def convert(self, value, param, ctx):
        if re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
                    value):
            return value
        self.fail(uxstring.UxString.Error.invalid_email)


class Username(click.ParamType):
    """ Param validator class for prompting user for username """
    name = "Username"

    def __init__(self):
        click.ParamType.__init__(self)

    def convert(self, value, param, ctx):
        if re.match(r"^[a-zA-Z0-9][a-zA-Z_0-9]+$", value):
            if len(value) > 4 and len(value) < 32:
                return value
        self.fail(uxstring.UxString.Error.invalid_username)
