import arrow
from calendar import timegm
from two1.lib.bitcoin.block import Block
from two1.lib.bitcoin.crypto import PublicKey
from two1.lib.bitcoin.hash import Hash
from two1.lib.bitcoin.script import Script
from two1.lib.bitcoin.txn import CoinbaseInput
from two1.lib.bitcoin.txn import Transaction
from two1.lib.bitcoin.txn import TransactionInput
from two1.lib.bitcoin.txn import TransactionOutput
from two1.lib.bitcoin.utils import bytes_to_str
from two1.lib.bitcoin.utils import difficulty_to_target
from two1.lib.bitcoin.utils import target_to_bits


def txn_from_json(txn_json):
    inputs = []
    for i in txn_json['inputs']:
        if 'output_hash' in i:
            outpoint = Hash(i['output_hash'])
            script = Script(bytes.fromhex(i['script_signature_hex']))
            inp = TransactionInput(outpoint,
                                   i['output_index'],
                                   script,
                                   i['sequence'])
        else:
            # Coinbase txn, we pass in a block version of 1 since the
            # coinbase script from api.chain.com already has the
            # height in there. Don't want our stuff to repack it in.
            inp = CoinbaseInput(txn_json['block_height'],
                                bytes.fromhex(i['coinbase']),
                                i['sequence'],
                                1)

        inputs.append(inp)

    outputs = []
    for o in txn_json['outputs']:
        scr = Script(bytes.fromhex(o['script_hex']))
        out = TransactionOutput(o['value'], scr)
        outputs.append(out)

    txn = Transaction(Transaction.DEFAULT_TRANSACTION_VERSION,
                      inputs,
                      outputs,
                      txn_json['lock_time'])

    return txn


def test_txn_serialization(txn_json):
    ''' txn_json: a JSON dict from api.chain.com that also contains
                 the raw hex of the transaction in the 'hex' key
    '''
    txn = txn_from_json(txn_json)
    txn_bytes = bytes(txn)
    txn_hash = txn.hash

    try:
        assert txn.num_inputs == len(txn_json['inputs'])
        assert txn.num_outputs == len(txn_json['outputs'])
        assert str(txn_hash) == txn_json['hash'], \
            "Hash does not match for txn: %s\nCorrect bytes:\n%s\nConstructed bytes:\n%s\nJSON:\n%s" % (
                txn_json['hash'],
                txn_json['hex'],
                bytes_to_str(txn_bytes),
                txn_json)
    except AssertionError as e:
        print(e)
        raise


def test_block(block_json):
    # Why is it so f*ing hard to get a UNIX-time from a time string?
    a = arrow.get(block_json['time'])
    time = timegm(a.datetime.timetuple())

    # TODO: Need to have a make_txn_from_json() method that's shared
    # between here and test_txn()
    txns = [txn_from_json(t) for t in block_json['transactions']]

    # Create a new Block object
    block = Block(block_json['height'],
                  block_json['version'],
                  Hash(block_json['previous_block_hash']),
                  time,
                  int(block_json['bits'], 16),
                  block_json['nonce'],
                  txns)

    block_hash = block.hash

    try:
        assert len(block.txns) == len(block_json['transactions'])
        assert block.height == block_json['height']
        assert block.block_header.version == block_json['version']
        assert block.block_header.prev_block_hash == Hash(block_json['previous_block_hash'])
        assert block.block_header.merkle_root_hash == Hash(block_json['merkle_root'])
        assert block.block_header.time == time
        assert block.block_header.bits == int(block_json['bits'], 16)
        assert block.block_header.nonce == block_json['nonce']
        assert block_hash == Hash(block_json['hash'])
        assert block.block_header.valid

    except AssertionError as e:
        print(e)
        print("block height:        %d" % (block.height))
        print("   from json:        %d" % (block_json['height']))
        print("     version:        %d" % (block.block_header.version))
        print("   from json:        %d" % (block_json['version']))
        print("   prev_block_hash:  %s" % (block.block_header.prev_block_hash))
        print("   from json:        %s" % (block_json['previous_block_hash']))
        print("   merkle_root_hash: %s" % (block.block_header.merkle_root_hash))
        print("   from json:        %s" % (block_json['merkle_root']))
        print("        time:        %d" % (block.block_header.time))
        print("   from json:        %d" % (time))
        print("        bits:        %d" % (block.block_header.bits))
        print("   from json:        %d" % (int(block_json['bits'], 16)))
        print("       nonce:        %d" % (block.block_header.nonce))
        print("   from json:        %d" % (block_json['nonce']))

        raise

def test_crypto():
    pts = ((0x50863ad64a87ae8a2fe83c1af1a8403cb53f53e486d8511dad8a04887e5b2352,
            0x2cd470243453a299fa9e77237716103abc11a1df38855ed6f2ee187e9c582ba6),
           (0xa83b8de893467d3a88d959c0eb4032d9ce3bf80f175d4d9e75892a3ebb8ab7e5,
            0x370f723328c24b7a97fe34063ba68f253fb08f8645d7c8b9a4ff98e3c29e7f0d),
           (0xf680556678e25084a82fa39e1b1dfd0944f7e69fddaa4e03ce934bd6b291dca0,
            0x52c10b721d34447e173721fb0151c68de1106badb089fb661523b8302a9097f5),
           (0x241febb8e23cbd77d664a18f66ad6240aaec6ecdc813b088d5b901b2e285131f,
            0x513378d9ff94f8d3d6c420bd13981df8cd50fd0fbd0cb5afabb3e66f2750026d))

    for pt in pts:
        b = bytes([(pt[1] & 0x1) + 0x2]) + pt[0].to_bytes(32, 'big')
        b_full = bytes([0x04]) + pt[0].to_bytes(32, 'big') + pt[1].to_bytes(32, 'big')
        pk = PublicKey.from_bytes(b)
        assert pk.point.y == pt[1]
        assert b == pk.compressed_bytes
        assert b_full == bytes(pk)


def test_utils():
    assert difficulty_to_target(16307.420938523983) == 0x404cb000000000000000000000000000000000000000000000000
    assert target_to_bits(0x00000000000404CB000000000000000000000000000000000000000000000000) == 0x1b0404cb


def test_txn():
    txn_str = "0100000001205607fb482a03600b736fb0c257dfd4faa49e45db3990e2c4994796031eae6e000000008b483045022100ed84be709227397fb1bc13b749f235e1f98f07ef8216f15da79e926b99d2bdeb02206ff39819d91bc81fecd74e59a721a38b00725389abb9cbecb42ad1c939fd8262014104e674caf81eb3bb4a97f2acf81b54dc930d9db6a6805fd46ca74ac3ab212c0bbf62164a11e7edaf31fbf24a878087d925303079f2556664f3b32d125f2138cbefffffffff0128230000000000001976a914f1fd1dc65af03c30fe743ac63cef3a120ffab57d88ac00000000"
    tx = Transaction.from_hex(txn_str)

    output_address = "1P4X54WbgeVKAnbKziaGP5n9b6Qvc9R8RZ"
    assert tx.output_index_for_address(output_address) == 0
    assert not tx.output_index_for_address("1CmzK6oqWMwdyo4J7f2vkQTd6uu1RwtERP")

    txn_str = "0100000002cb246d110b6087cd3b5e3d3b7a74505ea995721208ddfc15b6b3b718271e0b41010000006b48304502201f2cf747f9f8e3f770bef848e6787c9fca31e3086c390e505c1339936a15a78f022100a9e5f761162b8a4387c4009ce9469e92302fda68afe85371181b6e13b84f052d01210339e1274cd66db3dbe23e4def7ae9eb81644c15347cf0b39c741fb947c8ef1f12ffffffffb828405fca4f578073fe02bb00e999407bbaa3f5556f4c3571fd5fef28e47de8010000006a47304402206b7a8851fb2284201f31854bc857a8e1a1c4d5dbd19efe76d89d2c02083ff397022029a231c2750005b5ec4c437a8fa7163eaffe02e5fb51d9b8bb5edc5bb88040720121036744acff73b223a6f04190b60a980f8de1ed0271bba92144850e90c1af489fb3ffffffff0232530000000000001976a9146037aac7480f0fa0c7740560a7bf2f37ec17597988acb0ad01000000000017a914ef5a22f491632b2f18c59352dd64fa4ec346a8118700000000"

    tx = Transaction.from_hex(txn_str)

    output_address = "19mkZEZinQ77SrXbzxd5QJksikQFmfUNfo"
    assert tx.output_index_for_address(output_address) == 0

    output_address = "3PWbQBs5YDbmFCe5RdDjzqApJxs25Apvnd"
    assert tx.output_index_for_address(output_address) == 1
