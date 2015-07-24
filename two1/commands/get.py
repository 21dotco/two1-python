import click
from two1.config import pass_config

@click.command()
@pass_config
def get():
    "Get Bitcoin from the 21.co faucet"
    return
