import arrow
from calendar import timegm
import json
import pytest
from two1.bitcoin.utils import *
from two1.bitcoin.block import Block, BlockHeader
from two1.bitcoin.script import Script
from two1.bitcoin.txn import CoinbaseInput, Transaction, TransactionInput, TransactionOutput


def txn_from_json(txn_json):
    inputs = []
    for i in txn_json['inputs']:
        if 'output_hash' in i:
            outpoint = bytes.fromhex(i['output_hash'])[::-1] # In RPC order, need to make it internal
            script = Script(bytes.fromhex(i['script_signature_hex']), True)
            inp = TransactionInput(outpoint,
                                   i['output_index'],
                                   script,
                                   i['sequence'])
        else:
            # Coinbase txn, we pass in a block version of 1 since the coinbase script
            # from api.chain.com already has the height in there. Don't want our stuff
            # to repack it in.
            inp = CoinbaseInput(txn_json['block_height'],
                                bytes.fromhex(i['coinbase']),
                                i['sequence'],
                                1)

        inputs.append(inp)

    outputs = []    
    for o in txn_json['outputs']:
        scr = Script(bytes.fromhex(o['script_hex']), True)
        out = TransactionOutput(o['value'], scr)
        outputs.append(out)

    txn = Transaction(Transaction.DEFAULT_TRANSACTION_VERSION,
                      inputs,
                      outputs,
                      txn_json['lock_time'])

    return txn

def test_txn(txn_json):
    ''' txn_json: a JSON dict from api.chain.com that also contains
                 the raw hex of the transaction in the 'hex' key
    '''

    txn = txn_from_json(txn_json)
    txn_bytes = bytes(txn)
    txn_hash = txn.hash

    try:
        assert txn.num_inputs == len(txn_json['inputs'])
        assert txn.num_outputs == len(txn_json['outputs'])
        assert txn_hash == bytes.fromhex(txn_json['hash'])[::-1], \
            "Hash does not match for txn: %s\nCorrect bytes:\n%s\nConstructed bytes:\n%s\nJSON:\n%s" % (txn_json['hash'],
                                                                                                        txn_json['hex'],
                                                                                                        bytes_to_str(txn_bytes),
                                                                                                        txn_json)
    except AssertionError as e:
        print(e)
        raise
        
def test_block(block_json):
    # Why is it so f*ing hard to get a UNIX-time from a time string?
    #print("block keys = %r, time = %r" % (block_json.keys(), block_json['time']))
    a = arrow.get(block_json['time'])
    time = timegm(a.datetime.timetuple())

    # TODO: Need to have a make_txn_from_json() method that's shared
    # between here and test_txn()
    txns = [txn_from_json(t) for t in block_json['transactions']]
    
    # Create a new Block object
    block = Block(block_json['height'],
                  block_json['version'],
                  bytes.fromhex(block_json['previous_block_hash'])[::-1], # To internal order
                  time,
                  int(block_json['bits'], 16),
                  block_json['nonce'],
                  txns)

    block_hash = block.hash
    
    try:
        assert len(block.txns) == len(block_json['transactions'])
        assert block.height == block_json['height']
        assert block.block_header.version == block_json['version']
        assert block.block_header.prev_block_hash == bytes.fromhex(block_json['previous_block_hash'])[::-1]
        assert block.block_header.merkle_root_hash == bytes.fromhex(block_json['merkle_root'])[::-1]
        assert block.block_header.time == time
        assert block.block_header.bits == int(block_json['bits'], 16)
        assert block.block_header.nonce == block_json['nonce']
        assert block_hash == bytes.fromhex(block_json['hash'])[::-1]

    except AssertionError as e:
        print(e)
        print("block height:        %d" % (block.height))
        print("   from json:        %d" % (block_json['height']))
        print("     version:        %d" % (block.block_header.version))
        print("   from json:        %d" % (block_json['version']))
        print("   prev_block_hash:  %s" % (bytes_to_str(block.block_header.prev_block_hash)))
        print("   from json:        %s" % (bytes_to_str(bytes.fromhex(block_json['previous_block_hash'])[::-1])))
        print("   merkle_root_hash: %s" % (bytes_to_str(block.block_header.merkle_root_hash)))
        print("   from json:        %s" % (bytes_to_str(bytes.fromhex(block_json['merkle_root'])[::-1])))
        print("        time:        %d" % (block.block_header.time))
        print("   from json:        %d" % (time))
        print("        bits:        %d" % (block.block_header.bits))
        print("   from json:        %d" % (int(block_json['bits'], 16)))
        print("       nonce:        %d" % (block.block_header.nonce))
        print("   from json:        %d" % (block_json['nonce']))

        raise
