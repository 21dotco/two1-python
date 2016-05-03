"""View notifications from 21.co"""
# standard python imports
import logging

# 3rd party imports
import click

# two1 imports
from two1 import util

from two1.commands.util import decorators
from two1.commands.util import uxstring


# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@decorators.catch_all
@decorators.json_output
@decorators.capture_usage
def inbox(ctx):
    """View notifications from 21.co."""
    return _inbox(ctx.obj['config'], ctx.obj['client'])


def _inbox(config, client):
    """Show a list of notifications on a click pager.

    Args:
        config (Config): config object used for getting .two1 information
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.

    Returns:
        list: list of notifications in users inbox
    """
    prints = []

    notifications, has_unreads = get_notifications(config, client)
    if not notifications:
        logger.info("Inbox empty")
        return notifications

    if len(notifications) > 0:
        prints.append(uxstring.UxString.notification_intro)
        prints.extend(notifications)

    output = "\n".join(prints)
    logger.info(output, pager=True)

    if has_unreads:
        client.mark_notifications_read(config.username)

    return tuple(map(click.unstyle, notifications))


def get_notifications(config, client):
    """Use the rest client to get the inbox notifications and sort by unread messages first.

    Args:
        config (Config): config object used for getting .two1 information
        client (TwentyOneRestClient): rest client used for communication with the backend api

    Returns:
        (list, bool): tuple of a list of notifications sorted by unread first and True if there
            are unreads, False otherwise
    """
    resp = client.get_notifications(config.username, detailed=True)
    resp_json = resp.json()
    notifications = []
    if "messages" not in resp_json:
        return notifications
    unreads = resp_json["messages"]["unreads"]
    reads = resp_json["messages"]["reads"]
    if len(unreads) > 0:
        notifications.append(click.style("Unread Messages:\n", fg="blue"))
    for msg in unreads:
        message_line = create_notification_line(msg)
        notifications.append(message_line)

    if len(reads) > 0:
        notifications.append(click.style("Previous Messages:\n", fg="blue"))

    for msg in reads:
        message_line = create_notification_line(msg)
        notifications.append(message_line)

    return notifications, len(unreads) > 0


def create_notification_line(msg):
    """Create a formatted notification line from a message dict.

    Args:
        msg (dict): a raw inbox notification in dict format

    Returns:
        str: a formatted notification message
    """
    local_time = util.format_date(msg["time"])
    message_line = click.style("{} : {} from {}\n".format(local_time, msg["type"],
                                                          msg["from"]),
                               fg="cyan")
    message_line += "{}\n".format(msg["content"])
    return message_line
