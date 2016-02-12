import click

@click.command()
@click.pass_context
def help(ctx):
    """Show help and exit."""
    #pylint: disable=redefined-builtin
    print(ctx.parent.get_help())
