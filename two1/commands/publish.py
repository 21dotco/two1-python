import click
from two1.lib.util.uxstring import UxString

@click.command()
@click.pass_context
def publish(config):
    """Publish a machine-payable endpoint.
    """
    click.echo(UxString.publish_stub)
               
               


