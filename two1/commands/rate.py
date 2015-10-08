import click
from two1.commands.config import pass_config

from two1.commands.config import pass_config, TWO1_HOST
from two1.lib.server.rest_client import TwentyOneRestClient
from two1.lib.server.machine_auth import MachineAuth
#from decimal import Decimal, localcontext, ROUND_DOWN


@click.command()
@pass_config
def rate(config):
    "Rate a buyer or seller"
    return
