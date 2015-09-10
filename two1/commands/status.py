import time

import click
from two1.config import pass_config
from tabulate import tabulate
from two1.lib import rest_client
from two1.config import TWO1_HOST
from two1.uxstring import UxString
from two1.debug import dlog
import time
import datetime
from random import randint


@click.command()
@pass_config
def status(config):
    """View earned Bitcoin and configuration"""

    client = rest_client.TwentyOneRestClient(TWO1_HOST)

    foo = config.fmt()
    config.log('''
21.co Account''', fg='magenta')
    config.log('''\
    Username              : {}'''
               .format(config.username))

    config.log('''
Wallet''', fg='magenta')

    b_seed = ord(config.username[0])
    # balance_c = int(b_seed * 10000 + datetime.datetime.now().minute * 8000)
    # balance_u = int(b_seed * 10000 + (datetime.datetime.now().minute+1) * 8000)
    balance_c = config.wallet.confirmed_balance()
    balance_u = config.wallet.unconfirmed_balance()

    #    balance_c = config.wallet.confirmed_balance()
    try:
        bitcoin_address = config.wallet.current_address()
    except AttributeError:
        bitcoin_address = "Not Set"

    config.log('''\
    Balance (confirmed)   : {} Satoshi
    Balance (unconfirmed) : {} Satoshi
    Payout Address        : {}'''
               .format(balance_c, balance_u, bitcoin_address)
               )

    mining_p = int(time.time() / 9.0)
    try:
        share_data = client.get_shares(config.username)[config.username]
        shares = share_data["good"]
    except:
        shares = UxString.Error.data_unavailable

    config.log('''
Mining Proceeds''', fg='magenta')
    config.log('''\
    Mining Status         : Live
    Mining Proceeds       : {}
    Shares Sent           : {}'''
               .format(mining_p, shares)
               )

    status_endpoints(config)
    status_bought_endpoints(config)


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
