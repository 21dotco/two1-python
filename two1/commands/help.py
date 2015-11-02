import click

@click.command()
@click.pass_context
def help(ctx):
    """Show help and exit."""
    print(ctx.parent.get_help())
