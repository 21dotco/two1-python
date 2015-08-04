from two1.bitcoin import crypto
from two1.bitcoin.exceptions import *
from two1.bitcoin.script import *
from two1.bitcoin.utils import *


class TransactionInput(object):
    """ See https://bitcoin.org/en/developer-reference#txin

    Args:
        outpoint (bytes): 32-byte string containing the outpoint in 
                          internal byte order
        outpoint_index (uint): Index of the specific output to spend
                               the transaction from. Endianness: host
        script (Script): Script object (or a raw bytes in the case
                         of a Coinbase input)
        sequence_num (uint): Sequence number. Endianness: host
    """

    @staticmethod
    def from_bytes(b):
        """ Deserializes a byte stream into a TransactionInput.

        Args:
            b (bytes): byte stream starting with the outpoint.

        Returns:
            (ti, b) (tuple): First element of the tuple is the TransactionInput
                             object and the second is the remaining byte stream.
        """
        outpoint = b[0:32]
        outpoint_index, b1 = unpack_u32(b[32:])
        script, b1 = Script.from_bytes(b1)
        sequence_num, b1 = unpack_u32(b1)

        return (
            TransactionInput(outpoint,
                             outpoint_index,
                             script,
                             sequence_num),
            b1
        )

    def __init__(self, outpoint, outpoint_index, script, sequence_num):
        self.outpoint = outpoint
        self.outpoint_index = outpoint_index
        self.script = script
        self.sequence_num = sequence_num

    def __str__(self):
        """ Returns a human readable formatting of this input.

        Returns:
            s (str): A string containing the human readable input.
        """
        return (
            "TransactionInput(" +
            "Outpoint: %s " % (bytes_to_str(self.outpoint)) +
            "Outpoint Index: %d " % (self.outpoint_index) +
            "Script: %s " % (self.script) +
            "Sequence: %d)" % (self.sequence_num))
        
    def __bytes__(self):
        """ Serializes the object into a byte stream.

        Returns:
            b (bytes): byte stream containing the serialized input.
        """
        return (
            self.outpoint +
            pack_u32(self.outpoint_index) +
            pack_var_str(bytes(self.script)) +
            pack_u32(self.sequence_num)
        )


class CoinbaseInput(TransactionInput):
    """ See https://bitcoin.org/en/developer-reference#coinbase

    Args:
        height (uint): The height of the block coinbase is part of will go into.
                       Not required for version 1 blocks.
        raw_script (bytes): the bytes of the coinbase script. For block_version > 1
                            the height portion should NOT be included in this script.
        sequence (int): Unless you are Satoshi with a version 1 block, the default
                        is fine. If you are Satoshi, send me some of your private
                        keys and set this to 0.
        block_version (int): The version of the block this coinbase is a part of
                             or will go into. If raw_script already contains the
                             height of the block, this must be 1.
    """
    NULL_OUTPOINT = bytes(32)
    MAX_INT       = 0xffffffff

    def __init__(self, height, raw_script, sequence=MAX_INT, block_version=3):
        self.height = height
        if block_version == 1:
            scr = raw_script
        else:
            scr = pack_var_str(Script.build_push_int(self.height)) + raw_script

        # Coinbase scripts are basically whatever, so we don't
        # try to create a script object from them.

        super().__init__(self.NULL_OUTPOINT,
                         self.MAX_INT,
                         scr,
                         sequence)

    def __str__(self):
        """ Returns a human readable formatting of this input.

        Returns:
            s (str): A string containing the human readable input.
        """
        return (
            "CoinbaseInput(" +
            "Outpoint: %s " % (bytes_to_str(self.outpoint)) +
            "Outpoint Index: 0x%08x " % (self.outpoint_index) +
            "Script: %s " % (bytes_to_str(self.script)) +
            "Sequence: 0x%08x)" % (self.sequence_num))
        
    def __bytes__(self):
        """ Serializes the object into a byte stream.
        
        Returns:
            b (bytes): byte stream containing the serialized coinbase input.
        """
        return (
            self.outpoint +
            pack_u32(self.outpoint_index) +
            pack_var_str(self.script) +
            pack_u32(self.sequence_num)
        )


class TransactionOutput(object):
    """ See https://bitcoin.org/en/developer-reference#txout
    
    Args:
        value (int): Number of satoshis to be spent. Endianness: host
        script (Script): A pay-out script.
    """

    @staticmethod
    def from_bytes(b):
        """ Deserializes a byte stream into a TransactionOutput object.

        Args:
            b (bytes): byte-stream beginning with the value.

        Returns:
            (to, b) (tuple): First element of the tuple is a TransactionOutput, the
                             second is the remainder of the byte stream.
        """
        value, b0 = unpack_u64(b)
        script_len, b0 = unpack_compact_int(b0)

        return (TransactionOutput(value, Script(b0[:script_len])), b0[script_len:])

    def __init__(self, value, script):
        self.value = value
        self.script = script

    def __str__(self):
        """ Returns a human readable formatting of this output.

        Returns:
            s (str): A string containing the human readable output.
        """
        return (
            "TransactionOutput(" +
            "Value: %d satoshis " % (self.value) +
            "Script: %s)" % (self.script))

    def __bytes__(self):
        """ Serializes the object into a byte stream.

        Returns:
            b (bytes): byte stream containing the serialized transaction output.
        """
        return pack_u64(self.value) + pack_var_str(bytes(self.script))

    
class Transaction(object):
    """ See https://bitcoin.org/en/developer-reference#raw-transaction-format

    Args:
        version (int): Transaction version (should always be 1). Endianness: host
        inputs (list(TransactionInput)): all the inputs that spend bitcoin.
        outputs (list(TransactionOutput)): all the outputs to which bitcoin is sent.
        lock_time (int): Time or a block number. Endianness: host
    """

    DEFAULT_TRANSACTION_VERSION = 1 # There are no other versions currently
    HASH_CODE_TYPE = 1

    @staticmethod
    def from_bytes(b):
        """ Deserializes a byte stream into a Transaction.

        Args: 
            b (bytes): byte stream starting with the version.

        Returns:
            (tx, b) (tuple): First element of the tuple is the Transaction, second
                             is the remainder of the byte stream.
        """
        # First 4 bytes are version
        version = struct.unpack('<I', b[:4])[0]
        b1 = b[4:]

        # Work on inputs
        num_inputs, b1 = unpack_compact_int(b1)

        inputs = []
        for i in range(num_inputs):
            inp, b1 = TransactionInput.from_bytes(b1)
            inputs.append(inp)

        # Work on outputs
        num_outputs, b1 = unpack_compact_int(b1)

        outputs = []
        for o in range(num_outputs):
            out, b1 = TransactionOutput.from_bytes(b1)
            outputs.append(out)

        # Lock time
        lock_time = struct.unpack('<I', b1[:4])[0]

        return (Transaction(version, inputs, outputs, lock_time), b1[4:])

    def __init__(self, version, inputs, outputs, lock_time):
        self.version = version
        self.inputs = inputs
        self.outputs = outputs
        self.lock_time = lock_time

    @property
    def num_inputs(self):
        """ The number of inputs in the transaction.
        """
        return len(self.inputs)

    @property
    def num_outputs(self):
        """ The number of outputs in the transaction.
        """
        return len(self.outputs)

    def sign(self, private_keys):
        """ Signs the transaction.

            This function assumes that the pub key script
            (scriptPubKey) of the unspent transaction output (utxo)
            being spent is the input script. The script for each of
            the inputs *is modified* to contain the signature script
            (scriptSig) only if the public key contained in the
            scriptPubKey matches the public key derived from the
            private key provided for that input.
        
        Args:
            private_keys (list(str)): A list of Base58Check encoded 
               private keys, one for each input, with which to sign
               the transaction.
        """
        if len(private_keys) != self.num_inputs:
            raise ValueError("len(private_keys) = %d must be equal to the number of inputs (%d) in the transaction." %
                             (len(private_keys), self.num_inputs))
        
        # Since we assume that the inputs all have the correct utxo
        # scriptPubKey, we create a template txn first to sign.
        txn_template = bytes(self) + pack_u32(self.HASH_CODE_TYPE)

        # Now let's go through each of the inputs, derive the public-key
        # for it from the given private key and make sure that it matches
        # the one in the scriptPubKey.
        for i, ti in enumerate(self.inputs):
            pub_key = crypto.get_public_key(private_keys[i])
            address = crypto.address_from_public_key(pub_key, False)[1:]  # Need to strip off version byte

            # Now we need the public key hash from the input script
            script_pub_key_hash_hex = ti.script.get_hash160()
            if script_pub_key_hash_hex is None:
                raise ValueError("Couldn't find public key hash in input script for input %d!" % (i))

            script_pub_key_hash = bytes.fromhex(script_pub_key_hash_hex[2:])  # Strip off the 0x
            
            if address != script_pub_key_hash_hex:
                raise ValueError("Address derived from private key does not match scriptPubKey for input %d!" % (i))

            # If we've made it this far, we can sign & update the script
            sig = crypto.sign(dhash(txn_template), private_keys[i])
            script_sig = pack_var_str(sig + pack_u32(self.HASH_CODE_TYPE)) + pack_var_str(pub_key)
            ti.script = Script(script_sig)
    
    def __str__(self):
        """ Returns a human readable formatting of this transaction.

        Returns:
            s (str): A string containing the human readable transaction.
        """
        s = "Transaction: Version: %d, lock time: %d\nInputs:\n" % (self.version, self.lock_time)
        for i in self.inputs:
            s += "\t%s\n" % (i)

        s += "Outputs:\n"
        for o in self.outputs:
            s += "\t%s\n" % (o)
            
        return s
    
    def __bytes__(self):
        """ Serializes the object into a byte stream.
        
        Returns:
            b (bytes): The serialized transaction.
        """
        return (
            pack_u32(self.version) +                      # Version
            pack_compact_int(self.num_inputs) +           # Input count
            b''.join([bytes(i) for i in self.inputs]) +   # Inputs
            pack_compact_int(self.num_outputs) +          # Output count
            b''.join([bytes(o) for o in self.outputs]) +  # Outputs
            pack_u32(self.lock_time)                      # Lock time
        )

    @property
    def hash(self):
        """ Computes the hash of the transaction.

        Returns:
            dhash (bytes): Double SHA-256 hash of the serialized transaction.
        """
        return dhash(bytes(self))
