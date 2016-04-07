""" Launch a machine-payable endpoint on the current machine """
# standard python imports
import os
import time
import logging
import shutil
import subprocess
import platform

# 3rd party imports
import requests
import click
from tabulate import tabulate

# two1 imports
import two1.commands.util.decorators as decorators
import two1.commands.util.exceptions as exceptions
import two1.commands.util.uxstring as uxstring
import two1.commands.join as join
import two1.commands.publish as publish
import two1.commands.util.zerotier as zerotier
import two1.commands.util.nginx as nginx


# Creates a ClickLogger
logger = logging.getLogger(__name__)


# whitelisted apps
# also tobe done by 21.co api.
WHITELISTED_APPS = ['ping21']


@click.group(invoke_without_command=True)
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@click.option('-a', '--all',
              is_flag=True,
              help="Sell all aggregatable apps on 21.co/mkt")
def sell(ctx, **options):
    """
    Sell 21 apps on your 21 Bitcoin Computer.

\b
Usage
_____
\b
Sell all of the apps on the 21.co marketplace.
$ 21 sell --all

\b
List all of the apps you're currently selling.
$ 21 sell list

\b
See the help for list
$ 21 sell list --help

\b
Destroy one of your currently running apps
$ 21 sell destroy myapp

\b
See the help for list
$ 21 sell destroy --help
    """
    if options['all']:
        _sell(ctx.obj['client'], **options)
    else:
        # prints help messge when no subcommand is given
        if ctx.invoked_subcommand is None:
            logger.info(ctx.command.get_help(ctx))


def _sell(client, **options):
    """ Fetches all aggregatable apps and starts multiple server services

        Git clones all valid 21.co sellable apps on the market. These apps have been
        pre-approved and have a Procfile or index.py for ease of bringup.

    Args:
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        all (bool): if True, sells all supported apps, otherwise just sell the given app

    Raises:
        ServerRequestError: if server returns an error code other than 401
    """
    if options['all']:
        zt_address = zerotier.get_address('21market')
        if not zt_address:
            # join the 21market
            join._join(client, "21market")
            tries = 0
            while not zt_address and tries < 7:
                zt_address = zerotier.get_address('21market')
                time.sleep(1)
                tries += 1

        logger.info(uxstring.UxString.enabling_endpoints)
        total_daily_revenue = 0

        # checks the api to get a list of sellable apps
        for app in client.get_sellable_apps():
            enable_endpoint(app["name"], app["git"])

            logger.info(uxstring.UxString.hosted_market_app_revenue.format(
                app["name"],
                satoshi_to_usd(app["avg_earnings_request"])))
            publish._publish(
                client,
                "{}/{}".format(app["name"], "/manifest.yaml"),
                '21market',
                True,
                {
                    'host': "{}".format(zt_address),
                    'basePath': "/{}".format(app['name'])
                }
                )

            total_daily_revenue += app["avg_earnings_day"]

        logger.info(uxstring.UxString.estimated_daily_revenue.format(satoshi_to_usd(total_daily_revenue)))


def enable_endpoint(appname, app_url):
    """ Enable an endpoint, (Clone + Run)

    Does the following:
        Checks compatibility with the current machine.
        Installs requirements. (requirements.txt)
        Runs app under nginx + unicorn.

    Args:
        appame (str): name of the application.
        app_url (str): url of the application (should be github friendly).

    Returns:
        bool: True if app is correctly installed, otherwise False

    Raises:
        OSError: if the appication is not compatible with the target system.
    """
    # ensure the app given is valid
    if appname not in WHITELISTED_APPS:
        raise ValueError("App is not supported yet. Please stay tuned for updates.")

    if app_url.endswith(".git"):
        # clones the repo to the current directory
        clone_repo(appname, app_url)

        # Install all of the python requirements using pip
        install_python_requirements(appname)

        # Installs the required server side requirements
        install_server_requirements()

        # fires up nginx and starts server
        nginx.create_default_server()
        nginx.create_site_includes()
        nginx.create_systemd_file(appname)
        nginx.create_config(appname)
    else:
        raise exceptions.Two1Error(uxstring.UxString.error.url_not_supported)


@sell.command()
def list():
    """
    List all currently running apps
\b
(as seen in /etc/nginx/site-includes/)
    """
    # pylint: disable=redefined-builtin
    if os.path.isdir("/etc/nginx/site-includes/") and \
       len(os.listdir("/etc/nginx/site-includes/")) > 0:

        # gets apps enabled by using site-includes folder
        enabled_apps = os.listdir("/etc/nginx/site-includes/")

        logger.info(uxstring.UxString.listing_enabled_apps)
        enabled_apps_table = []
        headers = ('No.', 'App name', 'Url')
        for i, enabled_app in enumerate(enabled_apps):
            enabled_apps_table.append([i, enabled_app, "http://0.0.0.0/{}".format(enabled_app)])
        logger.info(tabulate(enabled_apps_table, headers=headers, tablefmt="psql",))
    else:
        logger.info(uxstring.UxString.no_apps_currently_running)


@sell.command()
@click.argument('appname')
def destroy(appname):
    """
    Stop/Remove a current app that is currently
    being run on the host.

\b
Stop worker processes and disable site from sites-enabled
    """
    if appname in os.listdir("/etc/nginx/site-includes/"):
        if nginx.destroy_app(appname):
            logger.info(uxstring.UxString.successfully_stopped_app.format(appname))
        else:
            logger.info(uxstring.UxString.failed_to_destroy_app)
    else:
        logger.info(uxstring.UxString.app_not_enabled)


def clone_repo(appname, url):
    """ Clones the given git repo

    Args:
        appame (str): name of the application.
        url (str): git repo url.

    Raises:
        Two1Error: if the git repo could not be cloned
    """
    if os.path.exists(appname):
        return

    try:
        subprocess.check_output(["git", "clone", url])
    except subprocess.CalledProcessError as e:
        raise exceptions.Two1Error(uxstring.UxString.error.repo_clone_fail.format(e))


def install_python_requirements(dirname):
    """ Install the python requirements needed to run the app

    Args:
        dirname (str): directory of the app

    Raises:
        Two1Error: if the requirements could not be installed
    """
    # gets the full path
    abspath = os.path.abspath(dirname)

    try:
        subprocess.check_output("sudo -H pip3 install -r {}/requirements.txt".format(abspath), shell=True)
    except subprocess.CalledProcessError as e:
        raise exceptions.Two1Error(uxstring.UxString.unsuccessfull_python_requirements.format(e))


def install_server_requirements():
    """ Install requirements needed to host an app using nginx.

        Uses apt-get and brew package managers to install deps.

    Raises:
        Two1Error: if any of the install commands fails or the systems package manager isn't
            supported.
    """
    try:
        # check for debian based systems
        if shutil.which("apt-get"):
            subprocess.check_output("sudo apt-get install -y --force-yes nginx", shell=True)
            subprocess.check_output("sudo -H pip3 install gunicorn", shell=True)

        # check if brew installed for Mac OSX systems
        elif shutil.which("brew"):
            subprocess.check_output("brew install nginx", shell=True)
            subprocess.check_output("sudo pip3 install gunicorn", shell=True)

        else:
            # tell them to go get brew of on a mac
            if "darwin" in platform.system().lower():
                raise exceptions.Two1Error(uxstring.UxString.install_brew)
            else:
                raise exceptions.Two1Error(uxstring.UxString.unsupported_package_manager.format(
                    click.style("brew & apt-get", bold=True, fg="red")))

    except (subprocess.CalledProcessError, OSError) as e:
        raise exceptions.Two1Error(uxstring.UxString.unsuccessfull_server_requirements.format(e))


def satoshi_to_usd(satoshis):
    """ Converts the given satoshi amount to usd in cents via google api

    Returns:
        float: value of satoshis given in cents

    Raises:
        HTTPError: if request wasn't successful
    """
    endpoint = "https://www.google.com/finance/getprices?q=BTCUSD&x=CURRENCY&i=60&p=1&f=c"
    response = requests.get(endpoint)
    response.raise_for_status()
    cents_per_satoshi = (float(response.text.split()[-1]) * 100) / 1e8
    return round(satoshis * cents_per_satoshi, 2)
