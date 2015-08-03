import click
from two1.config import pass_config

@click.command()
@pass_config
def publish(config):
    """Publish your endpoint to the MMM"""
    return config
