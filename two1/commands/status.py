import time

import click
from two1.commands.config import pass_config
from tabulate import tabulate
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST
from two1.lib.util.uxstring import UxString


@click.command()
@pass_config
def status(config):
    """View earned Bitcoin and configuration"""

    client = rest_client.TwentyOneRestClient(TWO1_HOST)

    status_account(config)
    status_wallet(config)
    status_shares(config, client)
    status_earnings(config, client)

    config.log("")
    # status_endpoints(config)
    # status_bought_endpoints(config)


def status_account(config):
    config.log('''
21.co Account''', fg='magenta')
    config.log('''\
    Username              : {}'''
               .format(config.username))

    config.log('''
Wallet''', fg='magenta')


def status_wallet(config):
    balance_c = config.wallet.confirmed_balance()
    balance_u = config.wallet.unconfirmed_balance()
    pending_transactions = balance_u - balance_c

    #    balance_c = config.wallet.confirmed_balance()
    try:
        bitcoin_address = config.wallet.current_address
    except AttributeError:
        bitcoin_address = "Not Set"

    config.log('''\
    Balance (confirmed)   :   {} Satoshi
    Pending Transactions  :   {} Satoshi
    Payout Address        :   {}'''
               .format(balance_c, pending_transactions, bitcoin_address)
               )


def status_endpoints(config):
    headers = \
        ("URL", "Price", "MMM?", "Description", "# Requests", "Earnings")

    endpoint_data = [
        ("misc/en2cn", 1000, "No", "English to Chinese", 27, 27000),
        ("dice/bet", 1000, "Yes", "Satoshi Dice", 127, -127000),
        ("numpy/eigen", 10000, "Yes", "Eigen Values", 7, 70000),
        ("blackjack/", 1000, "No", "Blackjack", 17, 17000),
        ("misc/cn2en", 2000, "No", "Chinese to English", 2, 4000),
    ]
    config.log('\n')
    config.log(tabulate(endpoint_data, headers=headers, tablefmt='psql'))


def status_bought_endpoints(config):
    headers = \
        ("Seller", "Resource", "Price", "Date")

    purchases = [
        ("peaceful_beast", "en2cn", 4000, "2015-08-21 12:25:35")
    ]
    config.log('\n')
    config.log(tabulate(purchases, headers=headers, tablefmt='psql'))


def status_earnings(config, client):
    try:
        data = client.get_earnings(config.username)[config.username]
        total_earnings = data["total_earnings"]
        total_payouts = data["total_payouts"]
        config.log('\nMining Proceeds', fg='magenta')
        config.log('''\
    Total Earnings        : {}
    Total Payouts         : {}'''
                   .format(none2zero(total_earnings),
                           none2zero(total_payouts))
                   )

        if "is_flushing" in data and data["is_flushing"]:
            config.log("\n" + UxString.flush_status, fg='green')

    except:
        pass


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
