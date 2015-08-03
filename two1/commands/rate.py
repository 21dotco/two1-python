import click
from two1.config import pass_config

@click.command()
@pass_config
def rate(config):
    "Rate a buyer or seller"
    return
