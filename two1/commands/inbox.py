from collections import deque
from datetime import date, datetime
import click
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST
from two1.lib.server.analytics import capture_usage
from two1.lib.util.decorators import json_output
from two1.lib.util.uxstring import UxString


@click.command()
@click.option('--debug', is_flag=True, default=False,
              help='Include debug logs.')
@json_output
def inbox(config, debug):
    """Shows a list of notifications for your account"""
    return _inbox(config, debug)


@capture_usage
def _inbox(config, debug):
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)

    prints = []

    notifications, has_unreads = get_notifications(config, client)
    if len(notifications) > 0:
        prints.append(UxString.notification_intro)
        prints.extend(notifications)

    logs = get_bc_logs(client, debug)
    prints.extend(logs)

    output = "\n".join(prints)
    config.echo_via_pager(output)

    if has_unreads:
        client.mark_notifications_read(config.username)

    return logs


def get_bc_logs(client, debug):

    prints = []
    response = client.get_earning_logs()
    logs = response["logs"]

    prints.append(UxString.log_intro)

    if not debug:
        logs = filter_rollbacks(logs)

    for entry in logs:

        prints.append(get_headline(entry))

        # reason
        prints.append(get_description(entry))
        prints.append("\n")

        # transaction details
        if entry["amount"] < 0 and "paid_to" in entry and "txns" in entry:
            prints.append(get_txn_details(entry))
            prints.append("\n")

    if len(prints) == 1:
        prints.append(UxString.empty_logs)

    return prints

def get_headline(entry):
    # headline
    local_date = datetime.fromtimestamp(entry["date"]).strftime("%Y-%m-%d %H:%M:%S")
    if entry["amount"] > 0:
        headline = UxString.debit_message.format(local_date, entry["amount"])
    elif entry["reason"] == "flush_payout" or entry["reason"] == "earning_payout":
        headline = UxString.blockchain_credit_message.format(local_date, entry["amount"],
                                                             -entry["amount"])
    else:
        headline = UxString.credit_message.format(local_date, entry["amount"])

    headline = click.style(headline, fg="cyan")
    return headline


def get_description(entry):
    reason = UxString.reasons.get(entry["reason"], entry["reason"])

    if "-" in entry["reason"]:
        buy_str = entry["reason"].split("-", 1)
        if entry["amount"] < 0 :
            reason = UxString.buy_message.format(buy_str[1], buy_str[0])
        else:
            reason = UxString.sell_message.format(buy_str[1], buy_str[0])

    description = "Description: {}".format(reason)
    return description


def get_txn_details(entry):
    paid = click.style("    Address paid to            : {}".format(entry["paid_to"]),
                       fg="cyan")
    txns = "    Blockchain Transaction(s)  : "

    for txn in entry["txns"]:
        txns += txn + " "

    txns = click.style(txns, fg="cyan")
    text = paid + "\n" + txns
    return text


def filter_rollbacks(logs):
    # due to the payout schedule, it is guaranteed that a rollback debit is preceded by a
    # payout credit. When we see a rollback, we need to both filter that rollback and
    # its matching payout. We are bound to find the matching payout in the next iteration
    rollbacks = {}
    result = []
    for entry in logs:
        if entry["reason"] and entry["reason"] == 'PayoutRollback':
            count_for_amount = rollbacks.get(entry["amount"], 0)
            rollbacks[-entry["amount"]] = count_for_amount + 1
        elif (entry["reason"] == "flush_payout" or entry["reason"] == "earning_payout") \
                and (entry["amount"] in rollbacks and rollbacks[entry["amount"]] > 0):
            rollbacks[entry["amount"]] -= 1
        else:
            result.append(entry)

    return result


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
