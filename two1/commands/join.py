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


@click.command()
@click.argument("network", default="21market")
@click.option('--status', is_flag=True, default=False,
              help='Show the status of all the networks that you have joined.')
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@decorators.check_notifications
def join(ctx, network, status):
    """Join a p2p network to buy/sell for BTC.

\b
Usage
-----
$ 21 join 21market

Join 21market network

$ 21 join --status

Shows the status of all the networks that you have joined
"""
    if status:
        show_network_status()
    else:
        _join(ctx.obj['client'], network)


def show_network_status():
    """ Prints the network status of the zerotier networks """
    networks_info = zerotier.get_all_addresses()
    if len(networks_info) == 0:
        logger.info(uxstring.UxString.no_network)
        return

    headers = ["Network Name", "Your IP"]
    rows = []
    for name, ip in networks_info.items():
        rows.append([name, ip])

    logger.info(tabulate(rows, headers, tablefmt="grid"))


def _join(client, network):
    """ Joins the given zerotier network

    Args:
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        network (str): the name of the network being joined. Defaults to 21market

    Raises:
        ServerRequestError: if server returns an error code other than 401
    """
    try:
        logger.info(uxstring.UxString.update_superuser)

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
