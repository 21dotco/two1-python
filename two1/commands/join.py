""" Two1 command to join various zerotier networks """
# standard python imports
import subprocess
import logging

# 3rd party imports
import click
from tabulate import tabulate

# two1 imports
from two1.commands.util import decorators
from two1.commands.util import uxstring
from two1.commands.util import zerotier
from two1.commands.util import exceptions


# Creates a ClickLogger
logger = logging.getLogger(__name__)


def getinput(msg, choices):
    while True:
        out = input(msg)
        if out in choices:
            return out
        else:
            print("Invalid choice. Please try again.")


@click.command()
@click.argument("network", default="21market")
@click.option('--status', is_flag=True, default=False,
              help='Show status of all networks that you have joined.')
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@decorators.check_notifications
def join(ctx, network, status):
    """Join a p2p network to buy/sell for BTC.

\b
Usage
-----
21 join            # Join 21's peer-to-peer network
21 join --status   # Confirm that you have joined
"""
    if status:
        show_network_status()
    else:
        logger.info(uxstring.UxString.join_network_beta_warning)
        response = getinput("I understand and wish to continue [y/n]: ", ["y", "n"])
        if response == "y":
            logger.info(uxstring.UxString.superuser_password)
            _join(ctx.obj['client'], network)
        else:
            logger.info(uxstring.UxString.join_network_beta_exit)


def show_network_status():
    """Print network status."""
    networks_info = zerotier.get_all_addresses()
    if len(networks_info) == 0:
        logger.info(uxstring.UxString.no_network)
    else:
        headers = ["Network Name", "Your IP"]
        rows = []
        for name, ip in networks_info.items():
            rows.append([name, ip])
        logger.info(tabulate(rows, headers, tablefmt="simple"))


def _join(client, network):
    """Join the given network.

    Args:
        client (two1.server.rest_client.TwentyOneRestClient) an object
            for sending authenticated requests to the TwentyOne
            backend
        network (str): the name of the network being joined. Defaults
        to 21market

    Raises:
        ServerRequestError: if server returns an error code other than 401
    """
    try:
        if zerotier.is_installed():
            # ensures the zerotier daemon is running
            zerotier.start_daemon()
        else:
            logger.info(uxstring.UxString.install_zerotier)
        zt_device_address = zerotier.device_address()
        response = client.join(network, zt_device_address)
        if response.ok:
            network_id = response.json().get("networkid")
            zerotier.join_network(network_id)
            logger.info(uxstring.UxString.successful_join.format(click.style(network, fg="magenta")))
    except exceptions.ServerRequestError as e:
        if e.status_code == 400:
            logger.info(uxstring.UxString.invalid_network)
        else:
            raise e
    except subprocess.CalledProcessError as e:
        logger.info(str(e))
