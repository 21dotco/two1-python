import click
from two1.uxstring import UxString
from two1.lib.update import update_two1_package
from two1.config import pass_config


@click.command()
@pass_config
def update(config):
    """ Keep 21 App up to date"""
    click.echo(UxString.update_check)
    update_two1_package(config, force_update_check=True)
