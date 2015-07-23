from collections import namedtuple
from two1.bitcoin.txn import CoinbaseInput, Transaction
from two1.bitcoin.sha256 import sha256 as sha256_midstate
from two1.bitcoin.utils import *


''' merkle_hash: SHA-256 byte string (internal byte order)
    left_child: MerkleNode object
    right_child: MerkleNode object
'''
MerkleNode = namedtuple('MerkleNode', ['hash', 'left_child', 'right_child'])


class BlockHeader(object):
    ''' See https://bitcoin.org/en/developer-reference#block-headers
        For definitions of hash byte order, see:
        https://bitcoin.org/en/developer-reference#hash-byte-order
    '''

    @staticmethod
    def from_bytes(b):
        version, b = unpack_u32(b)
        prev_block_hash, b = b[0:32], b[32:]
        merkle_root_hash, b = b[0:32], b[32:]
        time, b = unpack_u32(b)
        bits, b = unpack_u32(b)
        nonce, b = unpack_u32(b)

        return (
            BlockHeader(version,
                        prev_block_hash,
                        merkle_root_hash,
                        time,
                        bits,
                        nonce),
            b
        )

    def __init__(self, version, prev_block_hash, merkle_root_hash,
                 time, bits, nonce):
        ''' version: 32 bit uint (host endianness)
            prev_block_hash: SHA-256 byte string (internal byte order, i.e.
                             normal output of hashlib.sha256().digest())
            merkle_root_hash: SHA-256 byte string (internal byte order)
            time: 32 bit uint (host endianness)
            bits: 32 bit uint (host endianness)
            nonce: 32 bit uint (host endianness)

            When serializing the block, the 32-bit uints are converted
            to little-endian but the hashes remain in internal byte order.
        '''
        self.version = version
        self.prev_block_hash = prev_block_hash
        self.merkle_root_hash = merkle_root_hash
        self.time = time
        self.bits = bits
        self.nonce = nonce

    def __bytes__(self):
        return (
            pack_u32(self.version) +
            self.prev_block_hash +
            self.merkle_root_hash +
            pack_u32(self.time) +
            pack_u32(self.bits) +
            pack_u32(self.nonce)
        )

    @property
    def hash(self):
        return dhash(bytes(self))


class BlockBase(object):
    ''' A ~mostly~ abstract base class for blocks. 
    '''

    def __init__(self, height, version, prev_block_hash, time, bits):
        self.height = height

        self.block_header = BlockHeader(version,
                                        prev_block_hash,
                                        bytes(32),        # Fake merkle_root for now
                                        time,
                                        bits,
                                        0)                # Fake nonce also
        self.target = decode_compact_target(bits)

    @property
    def coinbase_transaction(self):
        pass

    @coinbase_transaction.setter
    def coinbase_transaction(self, cb_txn):
        pass
        
    def compute_hash(self, nonce):
        self.block_header.nonce = nonce
        return self.block_header.hash
        
    def check_valid_nonce(self, nonce):
        # Compute hash and reverse it so that it's in RPC order before
        # comparing
        h = int.from_bytes(self.compute_hash(nonce)[::-1], 'big')
        return h < self.target

    
class Block(BlockBase):
    ''' See https://bitcoin.org/en/developer-reference#serialized-blocks
    '''

    @staticmethod
    def from_bytes(b):
        bh, b = BlockHeader.from_bytes(b)
        num_txns, b = unpack_compact_int(b)
        txns = []
        for i in range(num_txns):
            t, b = Transaction.from_bytes(b)
            txns.append(t)

        return (
            Block(bh.version,
                  bh.prev_block_hash,
                  bh.time,
                  bh.bits,
                  bh.nonce,
                  txns),
            b
        )

    def __init__(self, height, version, prev_block_hash, time, bits, nonce, txns):
        ''' See BlockHeader for all param definitions except txns
            txns is a list of Transaction objects
            The merkle root is computed from the txns
        '''
        super().__init__(height, version, prev_block_hash, time, bits)
        self.block_header.nonce = nonce
        self.txns = txns

        self.merkle_tree = None
        self.invalidate()

    def invalidate(self):
        ''' Updates the merkle tree and block header
            if any changes to the underlying txns were made
        '''
        self.compute_merkle_tree()
        self.block_header.merkle_root_hash = self.merkle_tree.hash

    def invalidate_coinbase(self, merkle_node=None):
        ''' Optimized update of the merkle tree if only the
            coinbase has been updated/changed. The whole merkle
            tree is not computed. Instead, just the left edge is.
        '''
        if merkle_node is None:
            merkle_node = self.merkle_tree

        if(merkle_node.left_child is None and
           merkle_node.right_child is None):
            # This is the node corresponding to the coinbase, update hash
            merkle_node.merkle_hash = self.coinbase_tranaction.hash
            return
        else:
            self.invalidate_coinbase(merkle_node.left_child)

        merkle_node.merkle_hash = dhash(merkle_node.left_child.hash +
                                        merkle_node.right_child.hash)

        # If we're back at the root, update the blockheader
        if merkle_node is self.merkle_tree:
            self.block_header.merkle_hash = self.merkle_tree.hash

    def compute_merkle_tree(self):
        # Tree gets built bottom up
        level_nodes = [MerkleNode(t.hash, None, None) for t in self.txns]
        while True:
            if len(level_nodes) == 1:
                self.merkle_tree = level_nodes[0]  # This is the root
                return
            if len(level_nodes) % 2 != 0:
                # Make sure there are an even number of nodes
                level_nodes.append(level_nodes[-1])
            new_level = []
            for i in range(0, len(level_nodes), 2):
                left = level_nodes[i]
                right = level_nodes[i+1]
                n = MerkleNode(dhash(left.hash + right.hash), left, right)
                new_level.append(n)
            level_nodes = new_level

    @property
    def coinbase_transaction(self):
        return self.txns[0]

    @coinbase_transaction.setter
    def coinbase_transaction(self, cb_txn):
        ''' This overwrites the existing coinbase transaction
            cb_txn: Transaction object that has a CoinbaseInput object
                    as the only input
        '''
        if cb_txn.num_inputs != 1:
            raise ValueError("Coinbase transaction has more than one input!")
        if not isinstance(cb_txn.inputs[0], CoinbaseInput):
            raise TypeError("First input of Coinbase transaction is not of type CoinbaseInput")

        self.txns[0] = cb_txn

        # Now we need to update the merkle_tree and merkle_hash in blockheader
        self.invalidate_coinbase()

    @property
    def hash(self):
        return self.block_header.hash
        
    def __bytes__(self):
        return (
            bytes(self.block_header) +
            pack_compact_int(len(self.txns)) +
            b''.join([bytes(t) for t in self.txns])
        )


class CompactBlock(BlockBase):
    ''' This is a block representation that contains the minimum state
        required for mining purposes: a BlockHeader and the merkle hashes
        one-in from the left edge of the merkle tree.
    '''

    def __init__(self, height, version, prev_block_hash, time, bits, merkle_edge, cb_txn=None):
        ''' height: 32 bit uint (host endianness)
            version: 32 bit uint (host endianness)
            prev_block_hash: SHA-256 byte string (internal byte order, i.e.
                             normal output of hashlib.sha256().digest())
            time: 32 bit uint (host endianness)
            bits: 32 bit uint (host endianness)
            merkle_edge: a list of merkle hashes one-in from the left edge of
                         the merkle tree. This is the minimum state required
                         to compute the merkle_root if the coinbase txn changes.
            cb_txn: if provided, must be a Transaction object containing a 
                    CoinbaseInput. If not provided, use 
                    CompactBlock.coinbase_transaction = ... 
                    to set the transaction. This will ensure the merkle_root is
                    computed according to the new coinbase transaction.
        '''
        super().__init__(height, version, prev_block_hash, time, bits)
        self.block_header = BlockHeader(version,
                                        prev_block_hash,
                                        bytes(32),        # Fake merkle_root for now
                                        time,
                                        bits,
                                        0)                # Fake nonce also
        self.merkle_edge = merkle_edge

        if cb_txn is not None:
            self.coinbase_transaction = cb_txn
        else:
            self._cb_txn = None

    @property
    def coinbase_transaction(self):
        return self._cb_txn

    @coinbase_transaction.setter
    def coinbase_transaction(self, cb_txn):
        ''' cb_txn: a Transaction object that contains a CoinbaseInput
        '''
        self._cb_txn = cb_txn
        self._complete_merkle_edge()
        self._compute_midstate()

    # Private function to compute the left-most edge of the
    # merkle-tree and thus the root. Shouldn't be necessary for public
    # callers to call this.
    def _complete_merkle_edge(self):
        if self._cb_txn is None:
            # TODO: raise an error?
            return
        
        cur_hash = self._cb_txn.hash

        for e in self.merkle_edge:
            cur_hash = dhash(cur_hash + e)
            
        self.block_header.merkle_root_hash = cur_hash

    # Private function to compute midstate.
    def _compute_midstate(self):
        # midstate is taking the first 512-bits of the block header
        # and doing a sha256.update() on just that portion.
        h = sha256_midstate(bytes(self.block_header)[0:64])
        self._midstate = struct.pack('>8I', *h.mid_state)
