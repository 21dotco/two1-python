"""Earn bitcoin via microtasks."""
import logging

import click

from two1.commands.util import decorators
from two1.commands.util.uxstring import ux
from two1.commands.faucet import _faucet as do_faucet

logger = logging.getLogger(__name__)


@click.command()
@click.option('-i', '--invite', default=None,
              help="Earn bitcoin for inviting friends to 21.")
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def earn(ctx, invite):
    """ Earn bitcoin by doing microtasks.

\b
Note that only the faucet is currently available, but other microtasks are
coming soon!
"""
    username, client, wallet = \
        ctx.obj['username'], ctx.obj['client'], ctx.obj['wallet']
    return _earn(username, client, wallet, invite)


def _earn(username, client, wallet, invite):
    if invite:
        ux('earn_task_use_faucet')
    else:
        do_faucet(username, client, wallet)
    return 0
