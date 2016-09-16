""" Two1 command to join various zerotier networks """
# 3rd party imports
import click

# two1 imports
from two1.commands.util import decorators
from two1.commands.market import join_wrapper
from two1.commands.market import show_network_status


@click.command()
@click.argument("network", default="21mkt")
@click.option('--status', is_flag=True, default=False,
              help="Print network status.")
@click.option('-f', '--force', is_flag=True, default=False,
              help='Ignores the security warnings and force joins the network')
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@decorators.check_notifications
def join(ctx, network, status, force):
    """Join a p2p network to buy/sell for BTC.

\b
Usage
-----
21 join            # Join 21's peer-to-peer network
21 join --status   # Print network status.
"""
    if status:
        show_network_status()
    else:
        join_wrapper(ctx.obj['client'], network, force)
