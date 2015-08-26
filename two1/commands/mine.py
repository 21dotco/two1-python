from two1.bitcoin.crypto import PrivateKey
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
from two1.lib import rest_client, message_factory
import two1.config as cmd_config

from gen import swirl_pb2 as swirl


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
        mining_rest_client = rest_client.MiningRestClient(PrivateKey.from_random(),
                                                          cmd_config.TWO1_HOST)

        work_msg = mining_rest_client.get_work(username=config.username)
        msg_factory = message_factory.SwirlMessageFactory()
        work = msg_factory.read_object(work_msg.content)
        find_valid_nonce(config)

        message_id = 123
        enonce2 = b'4\x8a\x8b\x06'
        nonce = 2000001
        otime = int(time.time())
        req_msg = msg_factory.create_submit_request(message_id=message_id,
                                                    work_id=work.work_id,
                                                    enonce2=enonce2,
                                                    otime=otime,
                                                    nonce=nonce)

        client_message = swirl.SwirlClientMessage()
        reqq = req_msg[2:]
        client_message.ParseFromString(reqq)
        # take a look at the protobuf file to see what this means.
        message_type = client_message.WhichOneof("clientmessages")
        msg = getattr(client_message, message_type)
        mining_rest_client.send_work(username=config.username, data=req_msg)

        satoshi = random.randint(10000, 100000)
        config.log("You mined {} Satoshi".format(satoshi))
        try:
            bitcoin_address = config.bitcoin_address
        except AttributeError:
            bitcoin_address = "Not Set"

        b_seed = ord(config.username[0])
        balance_c = int(b_seed * 10000 + datetime.datetime.now().minute * 8000)
        balance_u = int(b_seed * 10000 + (datetime.datetime.now().minute + 1) * 8000)
        config.log("Waiting for Bitcoin to arrive...")
        time.sleep(3.0)
        config.log('''Wallet''', fg='magenta')
        config.log('''\
    Balance (confirmed)   : {} Satoshi
    Balance (unconfirmed) : {} Satoshi
    Payout Address        : {}
'''
                   .format(balance_c, balance_u, bitcoin_address)
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
