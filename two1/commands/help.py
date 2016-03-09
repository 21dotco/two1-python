# 3rd party imports
import click

# two1 imports
from two1.commands.util import decorators

@click.command()
@click.pass_context
@decorators.catch_all
def help(ctx):
    """Show help and exit."""
    #pylint: disable=redefined-builtin
    print(ctx.parent.get_help())
