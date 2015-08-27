from collections import namedtuple
import json
import sys
from two1.bitcoin.crypto import PrivateKey
from path import path
import click
from two1.config import pass_config
from two1.bitcoin.block import CompactBlock
from two1.mining.coinbase import CoinbaseTransactionBuilder
from two1.bitcoin.txn import TransactionOutput
from two1.bitcoin.utils import bytes_to_str
from two1.lib import login
import time
import random
import datetime
from two1.lib import rest_client, message_factory
import two1.config as cmd_config
from two1.bitcoin.hash import Hash

from two1.gen import swirl_pb2 as swirl


@click.command()
@pass_config
def mine(config):
    """Fastest way to get Bitcoin!"""
    # detect if hat is present
    bitcoinkit_present = False
    config.log("\nMining...")

    if bitcoinkit_present:
        # do minertop
        pass
    else:
        rest_client = rest_client.TwentyOneRestClient(cmd_config.TWO1_HOST,
                                                        login.get_auth_key())

        payout_address = config.wallet.current_address()
        config.log("Setting payout_address to {}".format(payout_address))
        # set a new address from the HD wallet for payouts
        rest_client.account_payout_address_post(config.username,payout_address)

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

        config.log("Mining Complete")
        payment_details = json.loads(payment_result.text)
        satoshi = payment_details["amount"]
        config.log("You mined {} ฿\n".format(satoshi), fg="yellow")
        try:
            bitcoin_address = config.bitcoin_address
        except AttributeError:
            bitcoin_address = "Not Set"

        config.log("Setting your payout address to {}\n".format(payout_address))
        balance_c = config.wallet.confirmed_balance()
        balance_u = config.wallet.unconfirmed_balance() + satoshi
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
        if nonce % 6e3 == 0:
            click.echo(click.style(u'█', fg='green'), nl=False)
        work.cb.block_header.nonce = nonce
        if work.cb.block_header.valid:
            share = Share(
                enonce2=enonce2,
                nonce=nonce,
                work_id=work_msg.work_id,
                otime=int(time.time()))
            #adds a new line at the end of progress bar
            click.echo("")
            return share


def get_enonces(username):
    enonce1_size = 8
    enonce1 = username[-1 * enonce1_size:].encode()
    if len(enonce1) != enonce1_size:
        enonce1 = enonce1 + ((enonce1_size - len(enonce1)) * b"0")
    enonce2_size = 4
    return enonce1, enonce2_size


def save_work(client, share, username):
    message_id = random.randint(1, 1e5)
    msg_factory = message_factory.SwirlMessageFactory()
    req_msg = msg_factory.create_submit_request(message_id=message_id,
                                                work_id=share.work_id,
                                                enonce2=share.enonce2,
                                                otime=share.otime,
                                                nonce=share.nonce)

    return client.send_work(username=username, data=req_msg)
