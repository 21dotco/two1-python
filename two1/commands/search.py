import click
from two1.lib.util.uxstring import UxString

@click.command()
@click.pass_context
def search(config):
    """Search for a machine-payable endpoint.
    """
    click.echo(UxString.search_stub)
