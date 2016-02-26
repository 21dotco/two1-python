# standard python imports
import platform
import subprocess

# 3rd party imports
import click
from tabulate import tabulate

# two1 imports
from two1.lib.server import rest_client
from two1.commands.util import decorators
from two1.commands.util import uxstring
from two1.commands.util import zerotier
from two1.commands.util import exceptions


@click.command()
@click.argument("network", default="21market")
@click.option('--status', is_flag=True, default=False,
              help='Show the status of all the networks that you have joined.')
@click.pass_context
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
        _join(ctx.obj['config'], ctx.obj['client'], network)


def show_network_status():
    """ Prints the network status of the zerotier networks

    Args:
        config (Config): config object used for getting .two1 information
    """
    networks_info = zerotier.get_all_addresses()
    if len(networks_info) == 0:
        click.secho(uxstring.UxString.no_network)
        return

    headers = ["Network Name", "Your IP"]
    rows = []
    for name, ip in networks_info.items():
        rows.append([name, ip])

    click.echo(tabulate(rows, headers, tablefmt="grid"))


def _join(config, client, network):
    """ Joins the given zerotier network

    Args:
        config (Config): config object used for getting .two1 information
        client (two1.lib.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        network (str): the name of the network being joined. Defaults to 21market

    Raises:
        ServerRequestError: if server returns an error code other than 401
    """
    try:
        config.log(uxstring.UxString.update_superuser)

        if zerotier.is_installed():
            # ensures the zerotier daemon is running
            zerotier.start_daemon()
        else:
            config.log(uxstring.UxString.install_zerotier)

        zt_device_address = zerotier.device_address()
        response = client.join(network, zt_device_address)
        if response.ok:
            network_id = response.json().get("networkid")
            zerotier.join_network(network_id)
            config.log(uxstring.UxString.successful_join.format(click.style(network, fg="magenta")))
    except exceptions.ServerRequestError as e:
        if e.status_code == 401:
            config.log(uxstring.UxString.invalid_network)
        else:
            raise e
    except subprocess.CalledProcessError as e:
        config.log(str(e))
