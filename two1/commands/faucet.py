"""Request bitcoin from the 21 faucet."""
import logging

import click

from two1.commands.mine import start_cpu_mining
from two1.commands.util import decorators
from two1.commands.util.uxstring import ux
from two1.commands.util.exceptions import MiningDisabledError

logger = logging.getLogger(__name__)


def _faucet(username, client, wallet):
    """Earn bitcoin from the 21 faucet.

    Because the client is untrusted in general, this command is
    rate-limited by CPU proof-of-work requested from the client, as
    well as heuristics applied to each username.
    """
    ux('earn_faucet_banner', fg='magenta')
    try:
        start_cpu_mining(username, client, wallet, prefix='earn_faucet')
    except MiningDisabledError as e:
        logger.info(e.args[0])
        return


@click.command()
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def faucet(ctx):
    """ Request bitcoin from the 21 faucet.

\b
Usage
-----
21 faucet  # Get bitcoin from 21's rate-limited faucet
"""
    username, client, wallet = \
        ctx.obj['username'], ctx.obj['client'], ctx.obj['wallet']
    return _faucet(username, client, wallet)
