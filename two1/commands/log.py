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
def log(config, debug):
    """Shows a list of events for your Bitcoin Computer"""
    return _log(config, debug)


@capture_usage
def _log(config, debug):
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)

    prints = []

    logs = get_bc_logs(client, debug)
    prints.extend(logs)

    output = "\n".join(prints)
    config.echo_via_pager(output)

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

