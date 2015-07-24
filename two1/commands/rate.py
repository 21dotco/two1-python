import click
from two1.config import pass_config

@click.command()
@pass_config
def rate():
    "Rate a buyer or seller"
    return
