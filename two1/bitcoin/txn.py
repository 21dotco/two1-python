import copy
import hashlib

from two1.bitcoin import crypto
from two1.bitcoin.exceptions import *
from two1.bitcoin.hash import Hash
from two1.bitcoin.script import *
from two1.bitcoin.utils import *


class TransactionInput(object):
    """ See https://bitcoin.org/en/developer-reference#txin

    Args:
        outpoint (Hash): A Hash object of the UTXO hash.
        outpoint_index (uint): Index of the specific output to spend
           the transaction from. Endianness: host
        script (Script): Script object (or a raw bytes in the case of
           a Coinbase input)
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
            TransactionInput(Hash(outpoint),
                             outpoint_index,
                             script,
                             sequence_num),
            b1
        )

    def __init__(self, outpoint, outpoint_index, script, sequence_num):
        if not isinstance(outpoint, Hash):
            raise TypeError("outpoint must be a Hash object.")
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
            "Outpoint: %s " % (self.outpoint) +
            "Outpoint Index: %d " % (self.outpoint_index) +
            "Script: %s " % (self.script) +
            "Sequence: %d)" % (self.sequence_num))
        
    def __bytes__(self):
        """ Serializes the object into a byte stream.

        Returns:
            b (bytes): byte stream containing the serialized input.
        """
        return (
            bytes(self.outpoint) +
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
    NULL_OUTPOINT = Hash(bytes(32))
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
            "Outpoint: %s " % (self.outpoint) +
            "Outpoint Index: 0x%08x " % (self.outpoint_index) +
            "Script: %s " % (bytes_to_str(self.script)) +
            "Sequence: 0x%08x)" % (self.sequence_num))
        
    def __bytes__(self):
        """ Serializes the object into a byte stream.
        
        Returns:
            b (bytes): byte stream containing the serialized coinbase input.
        """
        return (
            bytes(self.outpoint) +
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
    SIG_HASH_OLD = 0x00 # Acts the same as SIG_HASH_ALL
    SIG_HASH_ALL = 0x01
    SIG_HASH_NONE = 0x02
    SIG_HASH_SINGLE = 0x03
    SIG_HASH_ANY = 0x80

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

    def _copy_for_sig(self, input_index, hash_type, sub_script):
        """ Returns a copy of this txn appropriate for signing, based
            on hash_type.
        """
        new_txn = copy.deepcopy(self)

        # First deal w/the inputs
        
        # For the SIG_HASH_ANY case, we only care about
        # self.inputs[input_index]
        if hash_type == self.SIG_HASH_ANY:
            ti = new_txn.inputs[input_index]
            new_txn.inputs = [ti]
        else:
            for i, inp in enumerate(new_txn.inputs):
                inp.script = sub_script if i == input_index else Script("")
            
                if hash_type & 0x1f in [self.SIG_HASH_NONE, self.SIG_HASH_SINGLE] and input_index != i:
                    # Sequence numbers (nSequence) must be set to 0 for all but
                    # the input we care about.
                    inp.sequence_num = 0

        # Now deal with outputs
                    
        if hash_type & 0x1f == self.SIG_HASH_NONE:
            new_txn.outputs = []
        elif hash_type & 0x1f == self.SIG_HASH_SINGLE:
            # Resize output vector to input_index + 1
            new_txn.outputs = new_txn.outputs[:input_index+1]
            # All outputs except outputs[i] have a value of -1 (0xffffffff)
            # and a blank script
            for i, out in enumerate(new_txn.outputs):
                if i != input_index:
                    out.script = Script("")
                    out.value = 0xffffffff

        return new_txn
            
    def sign_input(self, input_index, hash_type, private_key, sub_script):
        """ Signs an input.
        
        Args:
            input_index (int): The index of the input to sign.
            hash_type (int): What kind of signature hash to do.
            private_key (crypto.PrivateKey): private key with which
               to sign the transaction.
            sub_script (Script): the scriptPubKey of the corresponding
               utxo being spent.
        """
        sub_scr = sub_script.remove_op("OP_CODESEPARATOR")
        
        if input_index < 0 or input_index >= len(self.inputs):
            raise ValueError("Invalid input index.")

        inp = self.inputs[input_index]

        compressed = False
        if hash_type & 0x1f == self.SIG_HASH_SINGLE and len(self.inputs) > len(self.outputs):
            # This is to deal with the bug where specifying an index that is out
            # of range (wrt outputs) results in a signature hash of 0x1 (little-endian)
            msg_to_sign = 0x1.to_bytes(32, 'little')
        else:
            txn_copy = self._copy_for_sig(input_index, hash_type, sub_scr)

            # Before signing we should verify that the address in the sub_script
            # corresponds to that of the private key
            script_pub_key_h160_hex = sub_scr.get_hash160()
            if script_pub_key_h160_hex is None:
                raise ValueError("Couldn't find public key hash in sub_script!")

            # first try uncompressed key
            h160 = None
            for compressed in [True, False]:
                h160 = private_key.public_key.hash160(compressed)
                if h160 != bytes.fromhex(script_pub_key_h160_hex[2:]):
                    h160 = None
                else:
                    break

            if h160 is None:
                raise ValueError("Address derived from private key does not match sub_script!")

            msg_to_sign = bytes(Hash.dhash(bytes(txn_copy) + pack_u32(hash_type)))
            
        sig = private_key.sign(msg_to_sign, False)

        if not private_key.public_key.verify(msg_to_sign, sig, False):
            return False

        if compressed:
            pub_key_str = pack_var_str(private_key.public_key.compressed_bytes)
        else:
            pub_key_str = pack_var_str(bytes(private_key.public_key))
        script_sig = pack_var_str(sig.to_der() + pack_compact_int(hash_type)) + pub_key_str
        inp.script = Script(script_sig)

        return True
    
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
        return Hash.dhash(bytes(self))
