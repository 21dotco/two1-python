from collections import deque
from datetime import date, datetime
import click
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST
from two1.lib.server.analytics import capture_usage
from two1.lib.util.decorators import json_output
from two1.lib.util.uxstring import UxString


@click.command()
@json_output
def inbox(config):
    """Shows a list of notifications for your account"""
    return _inbox(config)


@capture_usage
def _inbox(config):
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)

    prints = []

    notifications, has_unreads = get_notifications(config, client)
    if len(notifications) > 0:
        prints.append(UxString.notification_intro)
        prints.extend(notifications)

    output = "\n".join(prints)
    config.echo_via_pager(output)

    if has_unreads:
        client.mark_notifications_read(config.username)

    return notifications


def get_notifications(config, client):
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
    local_time = datetime.fromtimestamp(msg["time"]).strftime("%Y-%m-%d %H:%M")
    message_line = click.style("{} : {} from {}\n".format(local_time, msg["type"],
                                                          msg["from"]),
                               fg="cyan")
    message_line += "{}\n".format(msg["content"])
    return message_line
