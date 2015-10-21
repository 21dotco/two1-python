import time

import click
from two1.commands.config import pass_config
from tabulate import tabulate
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST
from two1.lib.server.analytics import capture_usage
from two1.lib.util.uxstring import UxString


@click.command()
@pass_config
def status(config):
    """View earned Bitcoin and configuration"""
    _status(config)


@capture_usage
def _status(config):
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)

    status_account(config)
    status_wallet(config, client)

    config.log("")
    # status_endpoints(config)
    # status_bought_endpoints(config)


def status_account(config):
    config.log('''\n21.co Account''', fg='magenta')
    config.log('''\
    Username              : {}'''
               .format(config.username))


SEARCH_UNIT_PRICE = 800
ARTICLE_UNIT_PRICE = 4000
MESSAGE_UNIT_PRICE = 8000


def status_wallet(config, client):
    total_balance, pending_transactions, flushed_earnings = _get_balances(config, client)

    try:
        bitcoin_address = config.wallet.current_address
    except AttributeError:
        bitcoin_address = "Not Set"

    config.log('''\nWallet''', fg='magenta')
    config.log('''\
    Your Spendable Balance   :   {} Satoshi
    Pending Debit or Credit  :   {} Satoshi'''
               .format(total_balance, pending_transactions)
               )

    if flushed_earnings > 0 :
        config.log('''\
    Your Flushed Amount      :   {} Satoshi *'''
                   .format(flushed_earnings))
    config.log('''\
    Your Bitcoin Address     :   {}'''
               .format(bitcoin_address))

    if flushed_earnings > 0:
        config.log(UxString.flush_status % flushed_earnings)
    buyable_searches = int(total_balance / SEARCH_UNIT_PRICE)
    buyable_articles = int(total_balance / ARTICLE_UNIT_PRICE)
    buyable_message = int(total_balance / MESSAGE_UNIT_PRICE)

    if total_balance == 0:
        config.log(UxString.status_empty_wallet.format(click.style("21 mine",
                                                                   bold=True)))
    else:
        config.log(UxString.status_exit_message.format(buyable_searches, buyable_articles,
                                                       buyable_message,
                                                       click.style("21 buy", bold=True),
                                                       click.style("21 buy --help",
                                                                   bold=True)))


def status_postmine_balance(config, client):
    total_balance, pending_transactions, flushed_earnings = _get_balances(config, client)
    try:
        bitcoin_address = config.wallet.current_address
    except AttributeError:
        bitcoin_address = "Not Set"

    config.log('''\nWallet''', fg='magenta')
    config.log('''\
    Your New Balance         :   {} Satoshi
    Your Bitcoin Address     :   {}'''
               .format(total_balance, bitcoin_address)
               )


def _get_balances(config, client):
    balance_c = config.wallet.confirmed_balance()
    balance_u = config.wallet.unconfirmed_balance()
    pending_transactions = balance_u - balance_c

    data = client.get_earnings(config.username)[config.username]
    total_earnings = data["total_earnings"]
    flushed_earnings = data["flush_amount"]

    total_balance = balance_c + total_earnings
    return total_balance, pending_transactions, flushed_earnings


def status_earnings(config, client):
    data = client.get_earnings(config.username)[config.username]
    total_earnings = data["total_earnings"]
    total_payouts = data["total_payouts"]
    config.log('\nMining Proceeds', fg='magenta')
    config.log('''\
    Total Earnings           : {}
    Total Payouts            : {}'''
               .format(none2zero(total_earnings),
                       none2zero(total_payouts))
               )

    if "flush_amount" in data and data["flush_amount"] > 0:
        flush_amount = data["flush_amount"]
        config.log('''\
    Flushed Earnings         : {}'''
                   .format(none2zero(flush_amount)),
                   )
        config.log("\n" + UxString.flush_status % flush_amount, fg='green')

def status_shares(config, client):
    try:
        share_data = client.get_shares(config.username)[config.username]
    except:
        share_data = None
    headers = ("", "Total", "Today", "Past Hour")
    data = []

    if share_data:
        try:
            for n in ["good", "bad"]:
                data.append(map(none2zero, [n, share_data["total"][n],
                                            share_data["today"][n],
                                            share_data["hour"][n]]))
        except KeyError:
            data = []  # config.log(UxString.Error.data_unavailable)

        if len(data):
            config.log("\nShare statistics:", fg="magenta")
            config.log(tabulate(data, headers=headers, tablefmt='psql'))
            # else:
            #    config.log(UxString.Error.data_unavailable)


def none2zero(x):
    # function to map None values of shares to 0
    return 0 if x is None else x
