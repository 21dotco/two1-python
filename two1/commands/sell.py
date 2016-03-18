"""
Launch a machine-payable endpoint on the current machine
"""
# standard python imports
import os
import time
import logging
import requests

# 3rd party imports
import click
from tabulate import tabulate

# two1 imports
import two1.commands.util.decorators as decorators
from two1.commands.util.uxstring import UxString
from two1.commands.helpers.sell_helpers import install_server_requirements
from two1.commands.helpers.sell_helpers import install_python_requirements
from two1.commands.helpers.sell_helpers import create_site_includes
from two1.commands.helpers.sell_helpers import create_default_nginx_server
from two1.commands.helpers.sell_helpers import create_systemd_file
from two1.commands.helpers.sell_helpers import create_nginx_config
from two1.commands.helpers.sell_helpers import destroy_app
from two1.commands.helpers.sell_helpers import detect_url
from two1.commands.helpers.sell_helpers import clone_repo
from two1.commands.publish import _publish
from two1.commands.publish import get_zerotier_address
from two1.commands.join import _join as join_zerotier_network
from two1.commands.util import zerotier


# Creates a ClickLogger
logger = logging.getLogger(__name__)

# satoshi to usd cents, should be moved to rest_client,
# data supplied via api.
satoshi_price = lambda : float(
        requests.get(
            "https://www.google.com/finance/getprices?q=BTCUSD&x=CURRENCY&i=60&p=1&f=c"
        ).text.split()[-1]
    ) / 1e8
satoshi_to_usd = lambda x: round(x * satoshi_price() * 100, 2)

# whitelisted apps
# also tobe done by 21.co api.
WHITELISTED_APPS = ['ping21']


@click.group(invoke_without_command=True)
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@click.option('-a', '--all',
              is_flag=True, help="Sell all available apps on 21.co/mkt")
def sell(ctx, **options):
    """
    Sell 21 Apps on your 21 Bitcoin Computer.

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
        # Fetch all valid 21.co sellable apps
        # on the market.
        # These apps have ben pre-approved and have
        # a style of standardization to them,
        # ie, a Procfile or standard index.py with variable "app"
        # that belongs to flask etc.
        # join zerotier network
        if not zerotier.get_address('21market'):
            join_zerotier_network(
                ctx.obj['config'],
                ctx.obj['client'],
                '21market'
            )
            tries = 0
            while not zerotier.get_address('21market') and tries < 7:
                time.sleep(1)
                tries += 1
        logger.info(UxString.enabling_endpoints)
        total_daily_revenue = 0
        for app in ctx.obj['client'].get_sellable_apps():
            if _enable_endpoint(
                app["name"],
                app["git"]
            ):
                logger.info(UxString.hosted_market_app_revenue.format(
                    app["name"],
                    satoshi_to_usd(app["avg_earnings_request"]),
                    )
                )
                _publish(
                    ctx.obj['config'],
                    ctx.obj['client'],
                    app["name"] + "/manifest.yaml",
                    '21market',
                    False,
                    {'host': get_zerotier_address('21market') +
                        "/" + app["name"]}
                    )
                total_daily_revenue += app["avg_earnings_day"]
        logger.info(UxString.estimated_daily_revenue.format(
                satoshi_to_usd(total_daily_revenue)
            )
        )


def _enable_endpoint(appname, app_url):
    """Enable an endpoint, (Clone + Run)

    Does the following:
        Checks compatibility with the current machine.
        Installs requirements. (requirements.txt)
        Runs app under nginx + unicorn.
    Args:
        appame (str): name of the application.
        app_url (str): url of the application (should be github friendly).

    Returns:
        bool : app is correctly installed.

    Raises:
        OSError: if the appication is not compatible with the
            target system.
    """
    if appname not in WHITELISTED_APPS:
        raise NotImplementedError(
            "App is not supported yet. Please stay tuned for updates."
        )
    if detect_url(app_url) == "git":
        clone_repo(appname, app_url)
        if not install_python_requirements(appname):
            return False
        if not install_server_requirements(appname):
            return False
        create_default_nginx_server()
        create_site_includes()
        create_systemd_file(appname)
        create_nginx_config(appname)
        return True


@sell.command()
@click.pass_context
def list(ctx):
    """
    List all currently running apps
\b
(as seen in /etc/nginx/site-includes/)
    """
    if os.path.isdir("/etc/nginx/site-includes/") \
            and len(os.listdir("/etc/nginx/site-includes/")) > 0:
        enabled_apps = os.listdir("/etc/nginx/site-includes/")
        logger.info(UxString.listing_enabled_apps)
        enabled_apps_table = []
        headers = ('No.', 'App name', 'Url')
        for i, enabled_app in enumerate(enabled_apps):
            enabled_apps_table.append([
                i,
                enabled_app,
                "http://0.0.0.0/{}".format(enabled_app)
                ])
        logger.info(tabulate(
            enabled_apps_table,
            headers=headers,
            tablefmt="psql",))
    else:
        logger.info(UxString.no_apps_currently_running)


@sell.command()
@click.argument('appname')
@click.pass_context
def destroy(ctx, appname):
    """
    Stop/Remove a current app that is currently
    being run on the host.

\b
Stop worker processes and disable site from sites-enabled
    """
    if appname in os.listdir("/etc/nginx/site-includes/"):
        if destroy_app(appname):
            logger.info(UxString.successfully_stopped_app.format(appname))
        else:
            logger.info(UxString.failed_to_destroy_app)
    else:
        logger.info(UxString.app_not_enabled)
