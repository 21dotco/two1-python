from datetime import date, datetime
import click
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST
from two1.lib.server.analytics import capture_usage
from two1.lib.util.uxstring import UxString


@click.command()
@click.option('--debug', is_flag=True, default=False,
              help='Include debug logs.')
@click.pass_context
def log(ctx, debug):
    """Shows the log of all the 21 earnings"""

    config = ctx.obj['config']
    _log(config, debug)


@capture_usage
def _log(config, debug):
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)

    response = client.get_earning_logs()

    logs = response["logs"]
    prints = []
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

    output = "\n".join(prints)
    click.echo_via_pager(output)


def get_headline(entry):
    # headline
    local_date = datetime.fromtimestamp(entry["date"]).strftime("%Y-%m-%d %H:%M:%S")
    headline = "{} : {} Satoshis".format(local_date, entry["amount"])
    if entry["amount"] > 0:
        color = "green"
    else:
        color = "red"
    headline = click.style(headline, fg=color)
    return headline


def get_description(entry):
    reason = UxString.reasons.get(entry["reason"], entry["reason"])

    if "-" in entry["reason"]:
        buy_str = entry["reason"].split("-", 1)
        reason = "Bought {} from {}".format(buy_str[1], buy_str[0])

    description = "Description: {}".format(reason)
    return description


def get_txn_details(entry):
    paid = click.style("    Address paid to          : {}".format(entry["paid_to"]),
                       fg="blue")
    txns = "    Blockchain Transactions  : "

    for txn in entry["txns"]:
        txns += txn + " "

    txns = click.style(txns, fg="blue")
    text = paid + "\n" + txns
    return text


def filter_rollbacks(logs):
    # due to the payout schedule, it is guaranteed that a rollback debit is preceded by a
    # payout credit. When we see a rollback, we need to both filter that rollback and
    # its matching payout. We are bound to find the matching payout in the next iteration
    result = []
    unmatched_rollback = None
    for entry in logs:
        if entry["reason"] and entry["reason"] == 'PayoutRollback':
            unmatched_rollback = entry
        elif unmatched_rollback and unmatched_rollback["amount"] == -entry["amount"]:
            unmatched_rollback = None
        else:
            result.append(entry)

    return result
