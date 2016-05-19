""" Two1 command to join various zerotier networks """
# standard python imports
import logging

# 3rd party imports
import click

# two1 imports
from two1.commands.util import decorators
from two1.commands.util import uxstring
from two1.commands.join import getinput
from two1.commands.join import show_network_status
from two1.commands.join import _join
from two1.commands.join import _leave

# Creates a ClickLogger
logger = logging.getLogger(__name__)


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
@decorators.capture_usage
@decorators.check_notifications
def status(ctx):
    """View the status of joined networks."""
    show_network_status()


@market.command()
@click.argument("network", default="21market")
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@decorators.check_notifications
def join(ctx, network):
    """Join 21's p2p network."""
    logger.info(uxstring.UxString.join_network_beta_warning)
    response = getinput("I understand and wish to continue [y/n]: ", ["y", "n"])
    if response == "y":
        logger.info(uxstring.UxString.superuser_password)
        _join(ctx.obj['client'], network)
    else:
        logger.info(uxstring.UxString.join_network_beta_exit)


@market.command()
@click.argument("network", default="21market")
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@decorators.check_notifications
def leave(ctx, network):
    """Leave 21's p2p network."""
    _leave(ctx.obj['client'], network)
