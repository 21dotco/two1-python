"""Open your 21.co profile in a web browser."""
# standard python imports
import logging
import webbrowser

# 3rd party importss
import click

# two1 imports
from two1 import TWO1_WWW_HOST
from two1.commands.util import decorators

# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@decorators.catch_all
@decorators.check_notifications
@decorators.capture_usage
def profile(ctx):
    """Open your 21.co profile in a web browser."""
    _profile(ctx.obj['config'].username)


def _profile(username):
    url = "%s/%s" % (TWO1_WWW_HOST, username)
    webbrowser.open(url)
