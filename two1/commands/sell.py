import click
from two1.config import pass_config

@click.command()
@pass_config
def sell(port=8000):
    "Set up a new machine-payable endpoint"
    endpoint = 'en2cn'
    click.echo('Selling %s on http://127.0.0.1:%d/' % (endpoint, port))
    return
