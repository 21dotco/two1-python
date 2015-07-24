import click
from two1.config import pass_config
from two1.debug import dlog

@click.command()
@pass_config
def buy(config):
    """Buy internet services with Bitcoin"""
    dlog("two1.buy")
    return 9
    

