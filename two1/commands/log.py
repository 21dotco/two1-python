"""View a log of 21 CLI events."""
# standart python imports
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
@click.option('--debug', is_flag=True, default=False,
              help='Include debug logs.')
@decorators.catch_all
@decorators.json_output
@decorators.capture_usage
def log(ctx, debug):
    """View a log of events of earning/spending BTC."""
    prints = []

    logs = get_bc_logs(ctx.obj['client'], debug)
    prints.extend(logs)

    output = "\n".join(prints)
    logger.info(output, pager=True)

    return tuple(map(click.unstyle, logs))


def get_bc_logs(client, debug):
    """Get a list of formatted log messages.

    Args:
        client (TwentyOneRestClient): rest client used for communication with the backend api.
        debug (bool): If True then no messages will be filtered out.

    Returns:
        list: A list of formatted log messages.
    """
    prints = []
    response = client.get_earning_logs()
    logs = response["logs"]

    prints.append(uxstring.UxString.log_intro)

    if not debug:
        logs = _filter_rollbacks(logs)

    for entry in logs:

        prints.append(_get_headline(entry))

        # reason
        prints.append(_get_description(entry))
        prints.append("\n")

        # transaction details
        if entry["amount"] < 0 and "paid_to" in entry and "txns" in entry:
            prints.append(_get_txn_details(entry))
            prints.append("\n")

    if len(prints) == 1:
        prints.append(uxstring.UxString.empty_logs)

    return prints


def _get_headline(entry):
    # headline
    local_date = util.format_date(entry["date"])

    if entry["amount"] > 0:
        headline = uxstring.UxString.debit_message.format(local_date, entry["amount"])
    elif entry["reason"] == "flush_payout" or entry["reason"] == "earning_payout":
        headline = uxstring.UxString.blockchain_credit_message.format(local_date, entry["amount"],
                                                                      -entry["amount"])
    else:
        headline = uxstring.UxString.credit_message.format(local_date, entry["amount"])

    headline = click.style(headline, fg="cyan")
    return headline


def _get_description(entry):
    reason = uxstring.UxString.reasons.get(entry["reason"], entry["reason"])

    if "-" in entry["reason"]:
        buy_str = entry["reason"].split("-", 1)
        if entry["amount"] < 0:
            reason = uxstring.UxString.buy_message.format(buy_str[1], buy_str[0])
        else:
            reason = uxstring.UxString.sell_message.format(buy_str[1], buy_str[0])

    description = "Description: {}".format(reason)
    return description


def _get_txn_details(entry):
    paid = click.style("    Address paid to            : {}".format(entry["paid_to"]),
                       fg="cyan")
    txns = "    Blockchain Transaction(s)  : "

    for txn in entry["txns"]:
        txns += txn + " "

    txns = click.style(txns, fg="cyan")
    text = paid + "\n" + txns
    return text


def _filter_rollbacks(logs):
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
