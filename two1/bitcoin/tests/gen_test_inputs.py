import json
import os
import random
import requests
import time

from two1.bitcoin.utils import *
from two1.bitcoin.script import Script
from two1.bitcoin.txn import TransactionInput, CoinbaseInput, TransactionOutput, Transaction
from two1.bitcoin.block import Block, BlockHeader

CHAIN_API_KEY = os.environ['CHAIN_API_KEY'] 
CHAIN_API_SECRET = os.environ['CHAIN_API_SECRET']

def get_from_chain(url_adder):
    url = 'https://api.chain.com/v2/bitcoin/%s' % (url_adder)

    ok = False
    while not ok:
        try:
            
            r = requests.get(url, auth=(CHAIN_API_KEY, CHAIN_API_SECRET))
            r.raise_for_status()
            ok = True
        except requests.HTTPError as e:
            if r.status_code == 429: # Too many requests
                time.sleep(1)
            else:
                print("Request was to %s" % (url))
                raise e
        
    b = json.loads(r.text)

    return b

def get_block(block):
    ''' block can be: a hash, index or "latest" '''
    blk = get_from_chain("blocks/%s" % (block))

    txns = []
    for t in blk['transaction_hashes']:
        txns.append(get_txn(t))

    blk['transactions'] = txns

    return blk

def get_txn(tx):
    tx_json = _get_txn(tx)
    raw_txn = _get_txn(tx_json['hash'], True)
    
    tx_json['hex'] = raw_txn['hex']

    return tx_json

def _get_txn(tx, raw=False):
    url_adder = "transactions/%s" % (tx)
    if raw:
        url_adder += '/hex'

    return get_from_chain(url_adder)


if __name__ == "__main__":
    last_block_index = get_block("latest")['height']
    print("last_block_index = %d" % (last_block_index))
    num_txns = 250
    full_blocks = 10

    block_indices = [random.randrange(0, last_block_index) for i in range(num_txns)]

    txns = []
    special_txns = ["52759f4ed9bf231014f040c7d0329e783aaa93cf973136d131b0cd55b9bf45cf",
                    "39409570293e8ec38970b0da814cbb826e75501036ac2f42836859b3ac8120ea",
                    "a258709e0f21a2cfdf053c3ee08b547dee1574179fbb964b37a43c7cd37c5f74"]

    for tx_hash in special_txns:
        tx = get_txn(tx_hash)
        txns.append(tx)

    blocks = []
    blocks_grabbed = 0
    for bi in block_indices:
        block_hash = rpc_conn.getblockhash(bi)
        block = rpc_conn.getblock(block_hash)

        b = None
        if blocks_grabbed < full_blocks:
            b = get_block(block_hash)
            blocks.append(b)
            txns += b['transactions']
            blocks_grabbed += 1
            print("blocks_grabbed = %d, block indices = %r" % (blocks_grabbed, [bl['height'] for bl in blocks]))

        if blocks_grabbed == full_blocks:
            with open("blocks.json", 'w') as f:
                json.dump(blocks, f)    


        got_tx = False
        while not got_tx:
            try:
                tx_num = random.randrange(0, len(block['tx']))

                tx = get_txn(block['tx'][tx_num])
                tx['block_version'] = block['version']
                txns.append(tx)
                got_tx = True
            except:
                pass

        print("block = %d (version: %d), using txn %d" % (bi, block['version'], tx_num))

    with open("txns.json", 'w') as f:
        json.dump(txns, f)
        
