from path import path
import click
from two1.config import pass_config

@click.command()
@pass_config
def mine(config):
    "Continously mine Bitcoin in the background"
    DEV_BITCOIN = "/dev/bitcoin"
    if path(DEV_BITCOIN).exists():
        print(DEV_BITCOIN + " exists")
    else:
        print(DEV_BITCOIN + " does not exist")
    return
