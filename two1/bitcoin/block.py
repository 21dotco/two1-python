"""This submodule provides the MerkleNode, Block, BlockHeader, and CompactBlock
classes. It allows you to work programmatically with the individual blocks in
the Bitcoin blockchain."""
from sha256 import sha256 as sha256_midstate

from two1.bitcoin.hash import Hash
from two1.bitcoin.txn import Transaction
from two1.bitcoin.utils import bytes_to_str, pack_u32, unpack_u32, bits_to_target, pack_compact_int, unpack_compact_int


class MerkleNode:
    """A MerkleNode object from which you can build a Merkle tree.

       Args:
           hash: SHA-256 byte string (internal byte order)
           left_child: MerkleNode object
           right_child: MerkleNode object
    """
    def __init__(self, hash=None, left_child=None, right_child=None):
        self.left_child = left_child
        self.right_child = right_child
        self.hash = hash


class BlockHeader(object):
    """ A BlockHeader object containing all fields found in a Bitcoin
        block header.

        Serialization & deserialization are done according to:
        https://bitcoin.org/en/developer-reference#block-headers
        For definitions of hash byte order, see:
        https://bitcoin.org/en/developer-reference#hash-byte-order

        Args:
            version (uint): The block version. Endianness: host
            prev_block_hash (Hash): a Hash object containing the
                previous block hash.
            merkle_root_hash (Hash): The merkle root hash.
            time (uint): Block timestamp. Endianness: host
            bits (uint): Compact representation of the difficulty. Endianness: host
            nonce (uint): Endianness: host
    """

    @staticmethod
    def from_bytes(b):
        """ Creates a BlockHeader object from a serialized
        bytestream. This function "eats" the bytestream and
        returns the remainder of the stream after deserializing
        the fields of the BlockHeader.

        Args:
            b (bytes): bytes beginning with the (4-byte) version.

        Returns:
            bh, b (tuple): A tuple containing two elements - a BlockHeader object
            and the remainder of the bytestream after deserialization.
        """
        version, b = unpack_u32(b)
        prev_block_hash, b = Hash(b[0:32]), b[32:]
        merkle_root_hash, b = Hash(b[0:32]), b[32:]
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
        if not isinstance(prev_block_hash, Hash):
            raise TypeError('prev_block_hash must be a Hash object')
        if not isinstance(merkle_root_hash, Hash):
            raise TypeError('merkle_root hash must be a Hash object')
        self.version = version
        self.prev_block_hash = prev_block_hash
        self.merkle_root_hash = merkle_root_hash
        self.time = time
        self.bits = bits
        self.nonce = nonce

        self.target = bits_to_target(bits)

    @property
    def valid(self):
        """ Dynamically returns whether hash < target

        Returns:
            valid (bool): True if hash < target, False otherwise.
        """
        return self.hash.to_int('little') < self.target

    def __str__(self):
        """ Gives the hex-encoded serialization of the header.

        Returns:
            str: hex-encoded string.
        """
        return bytes_to_str(bytes(self))

    def __bytes__(self):
        """ Serializes the BlockHeader object.

        Returns:
            byte_str (bytes): The serialized byte stream.
        """
        return (
            pack_u32(self.version) +
            bytes(self.prev_block_hash) +
            bytes(self.merkle_root_hash) +
            pack_u32(self.time) +
            pack_u32(self.bits) +
            pack_u32(self.nonce)
        )

    @property
    def hash(self):
        """ Computes the double SHA-256 hash of the serialized object.

        Returns:
            Hash: object containing the hash
        """
        return Hash.dhash(bytes(self))


class Block(object):
    """ A Bitcoin Block object.

    The merkle root is automatically computed from the transactions
    passed in during initialization.

    Serialization and deserialization are done according to:
    https://bitcoin.org/en/developer-reference#serialized-blocks

    Args:
        height (uint): Block height
        version (uint): The block version. Endianness: host
        prev_block_hash (Hash): a Hash object containing the
            previous block hash.
        time (uint): Block timestamp. Endianness: host
        bits (uint): Compact representation of the difficulty. Endianness: host
        nonce (uint): Endianness: host
        txns (list): List of Transaction objects
    """

    @staticmethod
    def from_bytes(b):
        """ Creates a Block from a serialized byte stream.

        Args:
            b (bytes): The byte stream, starting with the block version.

        Returns:
            block, b (tuple): A tuple. The first item is the deserialized block
            and the second is the remainder of the byte stream.
        """
        bh, b = BlockHeader.from_bytes(b)
        num_txns, b = unpack_compact_int(b)
        txns = []
        for i in range(num_txns):
            t, b = Transaction.from_bytes(b)
            txns.append(t)

        return Block.from_blockheader(bh, txns), b

    @classmethod
    def from_blockheader(cls, bh, txns):
        """ Creates a Block from an existing BlockHeader object and transactions.

        Args:
            bh (BlockHeader): A BlockHeader object.
            txns (list): List of all transactions to be included in the block.

        Returns:
            block (Block): A Block object.

        """
        self = cls.__new__(cls)
        self.block_header = bh
        self.transactions = txns

        self.merkle_tree = None
        self.invalidate()

        return self

    def __init__(self, height, version, prev_block_hash, time, bits, nonce, txns):
        self.block_header = BlockHeader(version,
                                        prev_block_hash,
                                        Hash(bytes(32)),  # Fake merkle_root for now
                                        time,
                                        bits,
                                        nonce)            # Fake nonce also

        self.height = height
        self.txns = txns

        self.merkle_tree = None
        self.invalidate()

    def invalidate(self):
        """ Updates the merkle tree and block header
            if any changes to the underlying txns were made.
        """
        self._compute_merkle_tree()
        self.block_header.merkle_root_hash = self.merkle_tree.hash

    def invalidate_coinbase(self):
        """ Optimized update of the merkle tree if only the
            coinbase has been updated/changed. The whole merkle
            tree is not computed. Instead, just the left edge is.
        """
        self._invalidate_coinbase()

    def _invalidate_coinbase(self, merkle_node=None):
        if merkle_node is None:
            merkle_node = self.merkle_tree

        if(merkle_node.left_child is None and
           merkle_node.right_child is None):
            # This is the node corresponding to the coinbase, update hash
            merkle_node.hash = self.coinbase_transaction.hash
            return
        else:
            self._invalidate_coinbase(merkle_node.left_child)

        merkle_node.hash = Hash.dhash(bytes(merkle_node.left_child.hash) +
                                      bytes(merkle_node.right_child.hash))

        # If we're back at the root, update the blockheader
        if merkle_node is self.merkle_tree:
            self.block_header.merkle_root_hash = self.merkle_tree.hash

    def _compute_merkle_tree(self):
        """ Computes the merkle tree from the transactions in self.transactions.
            The merkle root is the top node in the tree and can be accessed as
            self.merkle_tree.merkle_hash.
        """
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
                n = MerkleNode(Hash.dhash(bytes(left.hash) + bytes(right.hash)), left, right)
                new_level.append(n)
            level_nodes = new_level

    def get_merkle_edge(self):
        """ This function returns the merkle edge required for mining. Specifically,
        the edge begins with the first transaction after the coinbase (self.txns[1])
        and continues with all nodes in the tree, one-in from the left edge.

        Returns:
            edge (list): a list of hashes corresponding to the merkle edge
        """
        return self._get_merkle_edge()

    def _get_merkle_edge(self, node=None):
        # Start at root node and head recurse
        if node is None:
            if self.merkle_tree is None:
                self._compute_merkle_tree()
            node = self.merkle_tree

        r = node.right_child
        if r.left_child is None and r.right_child is None:
            # Leaf, so just return right_childs hash
            return [bytes(node.right_child.hash)]
        else:
            return self._get_merkle_edge(node.left_child) + [bytes(node.right_child.hash)]

    @property
    def coinbase_transaction(self):
        """ Setter/Getter for coinbase_transaction. The setter automatically
            calls invalidate_coinbase() to ensure the merkle root is recomputed
            based on the new coinbase transaction.
        """
        return self.txns[0]

    @coinbase_transaction.setter
    def coinbase_transaction(self, cb_txn):
        if cb_txn.num_inputs != 1:
            raise ValueError("Coinbase transaction has more than one input!")

        self.txns[0] = cb_txn

        # Now we need to update the merkle_tree and merkle_hash in blockheader
        self.invalidate_coinbase()

    @property
    def hash(self):
        """ Computes the hash of the block header.

        Returns:
            dhash (bytes): The double SHA-256 hash of the block header.
        """
        return self.block_header.hash

    def __bytes__(self):
        """ Serializes the Block object into a byte stream.

        Returns:
            b (bytes): The serialized byte stream.
        """
        return (
            bytes(self.block_header) +
            pack_compact_int(len(self.txns)) +
            b''.join([bytes(t) for t in self.txns])
        )


class CompactBlock(object):
    """ This is a block representation that contains the minimum state
        required for mining purposes: a BlockHeader and the merkle hashes
        one-in from the left edge of the merkle tree.

        Args:
            height (uint): Block height. Endianness: host
            version (uint): The block version. Endianness: host
            prev_block_hash (Hash): a Hash object containing the
                previous block hash.
            time (uint): Block timestamp. Endianness: host
            bits (uint): Compact representation of the difficulty. Endianness: host
            merkle_edge (list(Hash)): a list of merkle hashes one-in
                from the left edge of the merkle tree. This is the
                minimum state required to compute the merkle_root if
                the coinbase txn changes.
            cb_txn (Transaction): if provided, must contain a
                CoinbaseInput. If not provided, use
                CompactBlock.coinbase_transaction = ...  to set the
                transaction. This will ensure the merkle_root is
                computed according to the new coinbase transaction.
    """

    def __init__(self, height, version, prev_block_hash, time, bits, merkle_edge, cb_txn=None):
        self.block_header = BlockHeader(version,
                                        prev_block_hash,
                                        Hash(bytes(32)),  # Fake merkle_root for now
                                        time,
                                        bits,
                                        0)                # Fake nonce also
        self.height = height
        self.merkle_edge = merkle_edge

        if cb_txn is not None:
            self.coinbase_transaction = cb_txn
        else:
            self._cb_txn = None

    @property
    def coinbase_transaction(self):
        """cb_txn (Transaction): The coinbase transaction.
           The setter takes care of recomputing the merkle edge and
           midstate.
        """
        return self._cb_txn

    @coinbase_transaction.setter
    def coinbase_transaction(self, cb_txn):
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
            cur_hash = Hash.dhash(bytes(cur_hash) + bytes(e))

        self.block_header.merkle_root_hash = cur_hash

    # Private function to compute midstate.
    def _compute_midstate(self):
        # midstate is taking the first 512-bits of the block header
        # and doing a sha256.update() on just that portion.
        self._midstate, _ = sha256_midstate(bytes(self.block_header)[0:64]).state
