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


TWO1_MARKET = '21market'

# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.option('--join', is_flag=True, default=False,
              help="Join 21's peer-to-peer network.")
@click.option('--leave', is_flag=True, default=False,
              help="Leave 21's peer-to-peer network.")
@click.option('--status', is_flag=True, default=False,
              help='Show status of all networks that you have joined.')
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@decorators.check_notifications
def market(ctx, join, leave, status):
    """Join the peer-to-peer 21market network to buy/sell for BTC.

\b
Usage
-----
21 market --join     # Join 21's peer-to-peer network
21 market --leave    # Leave 21's peer-to-peer network
21 market --status   # Confirm that you have joined
"""
    if status:
        show_network_status()
    elif leave:
        _leave(ctx.obj['client'], TWO1_MARKET)
    else:
        logger.info(uxstring.UxString.join_network_beta_warning)
        response = getinput("I understand and wish to continue [y/n]: ", ["y", "n"])
        if response == "y":
            logger.info(uxstring.UxString.superuser_password)
            _join(ctx.obj['client'], TWO1_MARKET)
        else:
            logger.info(uxstring.UxString.join_network_beta_exit)
