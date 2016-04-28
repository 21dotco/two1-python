"""
Two1 command to update to the latest version of two1 and its dependencies.
"""
from datetime import date
import logging
import subprocess

import click

from two1.commands.util import decorators

# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@decorators.capture_usage
def update(ctx):
    """Update the 21 Command Line Interface.

\b
Usage
-----
Invoke this with no arguments to update the CLI.
$ 21 update
"""
    _update(ctx.obj['config'])


def _update(config):
    """
    Handles updating the CLI software including any dependencies.
    """
    config.set('last_update_check', date.today().strftime("%Y-%m-%d"), should_save=True)
    subprocess.call('curl https://21.co | sh', shell=True)
