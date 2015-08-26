import click
from two1.config import pass_config
from two1.debug import dlog
import time
import datetime
from random import randint

@click.command()
@pass_config
def status(config):
    """View earned Bitcoin and configuration"""

    foo = config.fmt()
    config.log('''
21.co Account''', fg='magenta')
    config.log('''\
    Username              : {}'''
         .format(config.username))

    config.log('''
Wallet''',fg='magenta')

    b_seed = ord(config.username[0])
    #balance_c = int(b_seed * 10000 + datetime.datetime.now().minute * 8000)
    #balance_u = int(b_seed * 10000 + (datetime.datetime.now().minute+1) * 8000)
    balance_c = config.wallet.confirmed_balance()
    balance_u = config.wallet.unconfirmed_balance()

#    balance_c = config.wallet.confirmed_balance()
    try:
      bitcoin_address = config.current_address
    except AttributeError:
      bitcoin_address = "Not Set"

    config.log('''\
    Balance (confirmed)   : {} Satoshi
    Balance (unconfirmed) : {} Satoshi
    Payout Address        : {}'''
      .format(balance_c,balance_u,bitcoin_address)
      )

    mining_p = int(time.time() / 9.0)
    shares = int(time.time() / 1.0)

    config.log('''
Mining Proceeds''',fg='magenta')
    config.log('''\
    Mining Status         : Live
    Mining Proceeds       : {}
    Shares Sent           : {}'''
      .format(mining_p,shares)
      )

    status_endpoints(config)
    status_bought_endpoints(config)

def status_endpoints(config):

    headers =  \
           ("URL","Price","MMM?","Description","# Requests","Earnings")
    header_format = "{:^15}|{:^10}|{:^5}|{:^25}|{:^10}|{:^12}"
    data_format   = "{:<15.15}|{:>10}|{:^5}|{:<25.25}|{:>10}|{:>12}"
    dundee1_format = "{:_^16}{:_^11}{:_^6}{:_^26}{:_^11}{:_^13}"
    dundee2_format = "{:_^15}|{:_^10}|{:_^5}|{:_^25}|{:_^10}|{:_^12}"

    endpoint_data = [
              ("misc/en2cn",1000,"No","English to Chinese",27,27000),
              ("dice/bet"  ,1000,"Yes","Satoshi Dice",127,-127000),
              ("numpy/eigen",10000,"Yes","Eigen Values",7,70000),
              ("blackjack/",1000,"No","Blackjack",17,17000),
              ("misc/cn2en",2000,"No","Chinese to English",2,4000),
    ]
    dundee_data = ["" for n in range(len(headers))]
    config.log("\nMMM Endpoints",fg="magenta")
    config.log(dundee1_format.format(*dundee_data))
    config.log(header_format.format(*headers))
    config.log(dundee2_format.format(*dundee_data))
    for edata in endpoint_data:
      config.log(data_format.format(*edata))
    config.log(dundee2_format.format(*dundee_data))
    config.log("")


def status_bought_endpoints(config):

    headers =  \
           ("Seller","Resource","Price","Date")
    header_format = "{:^15}|{:^15}|{:^12}|{:^25}"
    data_format   = "{:<15.15}|{:<15.15}|{:>12}|{:^25.25}"
    dundee1_format = "{:_^16}{:_^16}{:_^13}{:_^26}"
    dundee2_format = "{:_^15}|{:_^15}|{:_^12}|{:_^25}"

    purchases = config.get_purchases()

    dundee_data = ["" for n in range(len(headers))]
    config.log("\nMMM Purchases",fg="magenta")
    config.log(dundee1_format.format(*dundee_data))
    config.log(header_format.format(*headers))
    config.log(dundee2_format.format(*dundee_data))
    for edata in purchases:
      config.log(data_format.format(edata["s"],edata["r"],edata["p"],edata["d"]))
    config.log(dundee2_format.format(*dundee_data))
    config.log("")
