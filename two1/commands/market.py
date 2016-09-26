""" Two1 command to join various zerotier networks """
# standard python imports
import logging
import os
import platform
import subprocess
import sys

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


@click.group(invoke_without_command=True)
@click.pass_context
def market(ctx):
    """Join a p2p network to buy/sell for BTC.

\b
Usage
-----
21 market join     # Join 21's peer-to-peer network
21 market leave    # Leave 21's peer-to-peer network
21 market status   # Confirm that you have joined
"""
    if ctx.invoked_subcommand is None:
        logger.info(ctx.command.get_help(ctx))


@market.command()
@click.pass_context
@decorators.catch_all
@decorators.json_output
@decorators.capture_usage
@decorators.check_notifications
def status(ctx):
    """View the status of joined networks."""
    return show_network_status()


@market.command()
@click.argument("network", default="21mkt")
@click.option('-f', '--force', is_flag=True, default=False,
              help='Ignores the security warnings and force joins the network')
@click.pass_context
@decorators.catch_all
@decorators.json_output
@decorators.capture_usage
@decorators.check_notifications
def join(ctx, network, force):
    """Join 21's p2p network."""
    return join_wrapper(ctx.obj['client'], network, force)


@market.command()
@click.argument("network", default="21mkt")
@click.pass_context
@decorators.catch_all
@decorators.json_output
@decorators.capture_usage
@decorators.check_notifications
def leave(ctx, network):
    """Leave 21's p2p network."""
    return _leave(ctx.obj['client'], network)


def join_wrapper(client, network, force):
    if not force and not check_platform():
        logger.error(uxstring.UxString.join_unsupported_platform)
        sys.exit(1)

    logger.info(uxstring.UxString.join_network_beta_warning % network)
    response = getinput("I understand and wish to continue [y/n]: ", ["y", "n"])
    if response == "y":
        logger.info(uxstring.UxString.superuser_password)
        return _join(client, network)
    else:
        logger.info(uxstring.UxString.join_network_beta_exit)
        return {'joined': False, 'reason': 'did not wish to continue'}


def _join(client, network):
    """Join the given network.

    Args:
        client (two1.server.rest_client.TwentyOneRestClient) an object
            for sending authenticated requests to the TwentyOne
            backend
        network (str): the name of the network being joined. Defaults
        to 21mkt

    Raises:
        ServerRequestError: if server returns an error code other than 401
    """
    try:
        # ensures the zerotier daemon is running
        zerotier.start_daemon()
        zt_device_address = zerotier.device_address()
        response = client.join(network, zt_device_address)
        if response.ok:
            network_id = response.json().get("networkid")
            zerotier.join_network(network_id)
            logger.info(uxstring.UxString.successful_join.format(click.style(network, fg="magenta")))
            return {'joined': True}
    except exceptions.ServerRequestError as e:
        if e.status_code == 400:
            logger.info(uxstring.UxString.invalid_network)
            return {'joined': False, 'reason': 'invalid network'}
        else:
            raise e
    except subprocess.CalledProcessError as e:
        logger.info(str(e))
        return {'joined': False, 'reason': str(e)}


def _leave(client, network):
    """Join the given network.

    Args:
        client (two1.server.rest_client.TwentyOneRestClient) an object
            for sending authenticated requests to the TwentyOne
            backend
        network (str): the name of the network being joined. Defaults
        to 21mkt
    """
    # ensures the zerotier daemon is running
    zerotier.start_daemon()
    try:
        nwid = zerotier.get_network_id(network)
    except KeyError:
        logger.info('not in network')
        return {'left': False, 'reason': 'not in network'}
    try:
        zerotier.leave_network(nwid)
        logger.info(uxstring.UxString.successful_leave.format(click.style(network, fg="magenta")))
        return {'left': True}
    except subprocess.CalledProcessError as e:
        logger.info(str(e))
        return {'left': False, 'reason': str(e)}


def check_platform():
    """Check whether join is supported on the current platform.

    Due to security reasons, 21 join should only be allowed on Bitcoin Computers, Docker VMs,
    and EC2 machines.

    Returns:
        boolean: True if the os/platform is supported.
    """
    system = platform.system()
    distro = platform.platform()
    is_raspberry_pi = False
    try:
        info = open("/proc/cpuinfo").read()
    except FileNotFoundError:
        is_raspberry_pi = False
    else:
        # bcm2708: Raspberry Pi 1
        # bcm2709: Raspberry Pi 2
        # bcm2710: Raspberry Pi 3
        is_raspberry_pi = 'BCM27' in info or 'ODROID' in info

    return system == "Linux" and (
        os.path.isfile('/proc/device-tree/hat/uuid') or
        'boot2docker' in distro.lower() or
        is_raspberry_pi or
        os.path.isfile('/sys/hypervisor/uuid') or
        os.path.isdir('/var/lib/digitalocean')
    )


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

    return [{'network_name': name, 'ip': ip} for (name, ip) in networks_info.items()]
