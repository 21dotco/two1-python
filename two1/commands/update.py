"""
Two1 command to update to the latest version of two1 and its dependencies.
"""
import subprocess

import click


@click.command()
def update():
    """
    Update the 21 Command Line Interface.
    """
    subprocess.call('curl https://21.co | sh', shell=True)
