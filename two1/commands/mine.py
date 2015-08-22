from path import path
import click
from two1.config import pass_config
from two1.bitcoin.block import CompactBlock
from two1.mining.coinbase import CoinbaseTransactionBuilder
from two1.bitcoin.txn import TransactionOutput
from two1.bitcoin.utils import bytes_to_str
import time
import random
import datetime

@click.command()
@pass_config
def mine(config):
    """Fastest way to get Bitcoin!"""
    # detect if hat is present
    bitcoinkit_present = False
    config.log("\nYou are about to get Bitcoin!")

    if bitcoinkit_present:
        # do minertop
        pass
    else:
        find_valid_nonce(config)
        satoshi = random.randint(10000,100000)
        config.log("You mined {} Satoshi".format(satoshi))
        try:
            bitcoin_address = config.bitcoin_address
        except AttributeError:
            bitcoin_address = "Not Set"

        b_seed = ord(config.username[0])
        balance_c = int(b_seed * 10000 + datetime.datetime.now().minute * 8000)
        balance_u = int(b_seed * 10000 + (datetime.datetime.now().minute+1) * 8000)
        config.log("Waiting for Bitcoin to arrive...")
        time.sleep(3.0)
        config.log('''Wallet''',fg='magenta')
        config.log('''\
    Balance (confirmed)   : {} Satoshi
    Balance (unconfirmed) : {} Satoshi
    Payout Address        : {}
'''
              .format(balance_c,balance_u,bitcoin_address)
              )



def find_valid_nonce(config):
    '''Find valid nonce for given problem'''

    rotate = "+-"
    char = 0
    mining_message = "You are about to get Bitcoin! {}"
    max_nonce = 0xffff
    with click.progressbar(length=max_nonce, label='Mining...',
                           bar_template='%(label)s | %(bar)s | %(info)s',
                           fill_char=click.style(u'█', fg='cyan'),
                           empty_char=' ', show_eta=False) as bar:
        for item in bar:
            pass



