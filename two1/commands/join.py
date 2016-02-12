# standard python imports
import platform
import subprocess

# 3rd party imports
import click

# two1 imports
from tabulate import tabulate
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST
from two1.lib.server.analytics import capture_usage
from two1.lib.server.rest_client import ServerRequestError
from two1.lib.util.decorators import check_notifications
from two1.lib.util.uxstring import UxString
from two1.lib.util import zerotier


@click.command()
@click.argument("network", default="21market")
@click.option('--status', is_flag=True, default=False,
              help='Show the status of all the networks that you have joined.')
@click.pass_context
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
    config = ctx.obj['config']
    if status:
        show_network_status(config)
    else:
        _join(config, network)


@check_notifications
@capture_usage
def show_network_status(config):
    """ Prints the network status of the zerotier networks

    Args:
        config (Config): config object used for getting .two1 information
    """
    networks_info = zerotier.get_all_addresses()
    if len(networks_info) == 0:
        click.secho(UxString.no_network)
        return

    headers = ["Network Name", "Your IP"]
    rows = []
    for name, ip in networks_info.items():
        rows.append([name, ip])

    click.echo(tabulate(rows, headers, tablefmt="grid"))


@check_notifications
@capture_usage
def _join(config, network):
    """ Joins the given zerotier network

    Args:
        config (Config): config object used for getting .two1 information
        network (str): the name of the network being joined. Defaults to 21market

    Raises:
        ServerRequestError: if server returns an error code other than 401
    """
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)

    try:
        config.log(UxString.update_superuser)
        user_platform = platform.system()
        if user_platform != "Darwin":
            start_zerotier_command = [
                "sudo", "service", "zerotier-one", "start"
            ]
            subprocess.check_output(start_zerotier_command)
        zt_device_address = zerotier.device_address()
        response = client.join(network, zt_device_address)
        if response.ok:
            join_command = [
                "sudo", "zerotier-cli", "join",
                response.json().get("networkid")
            ]
            subprocess.check_output(join_command)
            config.log(UxString.successful_join.format(click.style(network, fg="magenta")))
    except ServerRequestError as e:
        if e.status_code == 401:
            config.log(UxString.invalid_network)
        else:
            raise e
    except subprocess.CalledProcessError as e:
        config.log(str(e))
