import click
from two1.lib.util.uxstring import UxString

@click.command()
@click.pass_context
def rate(config):
    """Rate a machine-payable endpoint.
    """
    click.echo(UxString.rate_stub)
