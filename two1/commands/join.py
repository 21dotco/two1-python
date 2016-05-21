""" Two1 command to join various zerotier networks """
# 3rd party imports
import click

# two1 imports
from two1.commands.util import decorators
from two1.commands.market import join_wrapper


@click.command()
@click.argument("network", default="21market")
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@decorators.check_notifications
def join(ctx, network):
    """Join a p2p network to buy/sell for BTC.

\b
Usage
-----
21 join            # Join 21's peer-to-peer network
"""
    join_wrapper(ctx.obj['client'], network)
