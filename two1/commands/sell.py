import click
from two1.lib.util.uxstring import UxString

@click.command()
@click.pass_context
def sell(config):
    """Sell a machine-payable endpoint.
    """
    click.echo(UxString.sell_stub)
