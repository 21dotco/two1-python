""" Two1 command help """
# standard python imports
import logging

# 3rd party imports
import click

# two1 imports
from two1.commands.util import decorators


# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@decorators.catch_all
def help(ctx):
    """Show help and exit."""
    # pylint: disable=redefined-builtin
    logger.info(ctx.parent.get_help())
