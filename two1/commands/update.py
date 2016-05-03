"""
Two1 command to update to the latest version of two1 and its dependencies.
"""
import subprocess

import click


@click.command()
def update():
    """
    Update your 21 installation.
    """
    subprocess.call('curl https://21.co | sh', shell=True)
