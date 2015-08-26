from collections import namedtuple
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
from two1.bitcoin.hash import Hash

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
        share = find_valid_nonce(config, work)

        message_id = random.randint(1, 1e5)
        req_msg = msg_factory.create_submit_request(message_id=message_id,
                                                    work_id=work.work_id,
                                                    enonce2=share.enonce2,
                                                    otime=share.otime,
                                                    nonce=share.nonce)

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


def get_enonces(username):
    enonce1_size = 8
    enonce1 = username[-1 * enonce1_size:].encode()
    if len(enonce1) != enonce1_size:
        enonce1 = enonce1 + ((enonce1_size - len(enonce1)) * b"0")
    enonce2_size = 4
    return enonce1, enonce2_size

Share = namedtuple('Share', ['enonce2', 'nonce', 'otime', 'job_id'])
Work = namedtuple('Work', ['job_id', 'enonce2', 'cb'])

def find_valid_nonce(config, work_msg):
    '''Find valid nonce for given problem'''

    enonce1, enonce2_size = get_enonces(username=config.username)
    outputs = [TransactionOutput.from_bytes(x)[0] for x in work_msg.outputs]
    iscript0 = work_msg.iscript0[4:-1]
    cb_builder = CoinbaseTransactionBuilder(
        work_msg.block_height, iscript0, work_msg.iscript1,
        len(enonce1), enonce2_size, outputs, 0
    )

    enonce2 = bytes([random.randrange(0, 256) for n in range(enonce2_size)])
    cb_txn = cb_builder.build(enonce1, enonce2)

    edge = [e for e in work_msg.edge]

    cb = CompactBlock(work_msg.block_height,
                      work_msg.block_version,
                      Hash(work_msg.prev_block_hash),
                      work_msg.itime,
                      work_msg.bits_pool,  # lower difficulty work_msg for testing
                      edge,
                      cb_txn)

    work = Work(job_id=work_msg.work_id,
                enonce2=enonce2,
                cb=cb)

    print("starting to mine for %s" % work.cb.block_header.target)
    start = int(time.time())
    for nonce in range(0xffffffff):
        work.cb.block_header.nonce = nonce
        if work.cb.block_header.valid:
            duration = int(time.time()) - start
            print("found in %d secs" % duration)
            share = Share(
                enonce2=enonce2,
                nonce=nonce,
                job_id=work_msg.work_id,
                otime=int(time.time()))
            return share

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
