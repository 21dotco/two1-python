from two1.bitcoin.exceptions import *
from two1.bitcoin.script import *
from two1.bitcoin.utils import *


class TransactionInput(object):
    ''' See https://bitcoin.org/en/developer-reference#txin
    '''

    @staticmethod
    def from_bytes(b):
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
        ''' outpoint: byte string (length 32) containing the outpoint
            outpoint_index: normal integer (host-endianness)
            script: Script object (or a raw bytes in the case
                    of a Coinbase input)
            sequence_num: normal integer (host-endianness)
        '''
        self.outpoint = outpoint
        self.outpoint_index = outpoint_index
        self.script = script
        self.sequence_num = sequence_num

    def __bytes__(self):
        return (
            self.outpoint +
            pack_u32(self.outpoint_index) +
            pack_var_str(bytes(self.script)) +
            pack_u32(self.sequence_num)
        )


class CoinbaseInput(TransactionInput):
    ''' See https://bitcoin.org/en/developer-reference#coinbase
    '''
    NULL_OUTPOINT = bytes(32)
    MAX_INT       = 0xffffffff

    def __init__(self, height, raw_script, sequence=MAX_INT, block_version=3):
        ''' height: unsigned integer containing the height of the block
                    this coinbase is part of will go into. Not required for
                    version 1 blocks.
            raw_script: the bytes of the coinbase script. For block_version > 1
                        the height portion should NOT be included in this script.
            sequence: Unless you are Satoshi with a version 1 block, the default
                      is fine. If you are Satoshi, send me some of your private
                      keys and set this to 0.
            block_version: The version of the block this coinbase is a part of
                           or will go into. If raw_script already contains the
                           height of the block, this must be 1.
        '''
        self.height = height
        if block_version == 1:
            scr = raw_script
        else:
            scr = pack_height(self.height) + raw_script

        # Coinbase scripts are basically whatever, so we don't
        # try to create a script object from them.

        super().__init__(self.NULL_OUTPOINT,
                         self.MAX_INT,
                         scr,
                         sequence)

    def __bytes__(self):
        return (
            self.outpoint +
            pack_u32(self.outpoint_index) +
            pack_var_str(self.script) +
            pack_u32(self.sequence_num)
        )


class TransactionOutput(object):
    ''' See https://bitcoin.org/en/developer-reference#txout
    '''

    @staticmethod
    def from_bytes(b):
        value, b0 = unpack_u64(b)
        script_len, b0 = unpack_compact_int(b0)

        return (TransactionOutput(value, b0[:script_len]), b0[script_len:])

    def __init__(self, value, script):
        self.value = value
        self.script = script

    def __bytes__(self):
        return pack_u64(self.value) + pack_var_str(bytes(self.script))

    
class Transaction(object):
    ''' See
        https://bitcoin.org/en/developer-reference#raw-transaction-format
    '''
    DEFAULT_TRANSACTION_VERSION = 1 # There are no other versions currently

    @classmethod
    def from_bytes(cls, b):
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
        return len(self.inputs)

    @property
    def num_outputs(self):
        return len(self.outputs)

    def __bytes__(self):
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
        return dhash(bytes(self))
