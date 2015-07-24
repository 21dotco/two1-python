from two1.bitcoin.utils import *
from two1.bitcoin.script import Script
from two1.bitcoin.txn import CoinbaseInput, TransactionInput, TransactionOutput, Transaction


class BitshareCoinbaseTransaction(Transaction):
    ''' This class is identical to Transaction except provides an additional
        method to serialize specifically for the client, meaning it removes
        the last output (assumes the last one is the Bitshare output) and the
        locktime, before returning the raw bytes.
    '''

    def __init__(self, version, inputs, outputs, lock_time):
        ''' Same semantics as Transaction and should include *ALL*
            outputs, including the Bitshare-added output.
        '''
        super().__init__(version, inputs, outputs, lock_time)
        self.bitshare_output_length = len(bytes(outputs[-1]))

    def client_serialize(self):
        b = bytes(self)
        remove_len = self.bitshare_output_length + 4  # 4 is for the lock-time
        return b[:-remove_len]


class CoinbaseTransactionBuilder(object):
    ''' See: https://bitcoin.org/en/developer-reference#coinbase
        Builds a coinbase txn:
        Creates a single input with no outpoint. The input script is defined as
        block height, iscript0, enonce1, enonce2, iscript1.

        iscript0 & iscript1 are random strings provided by the caller
        enonce1 is completed by the pool server
        enonce2 is completed by the pool client

        outputs is a list of TransactionOutput objects (*not* byte strings)
    '''

    def __init__(self, height, iscript0, iscript1, enonce1_len, enonce2_len, outputs, lock_time):
        self.height = height
        self.script_prefix = iscript0
        self.script_postfix = iscript1
        self.enonce1_len = enonce1_len
        self.enonce2_len = enonce2_len
        self.outputs = outputs
        self.lock_time = lock_time

        self.bitshare_padding = self.required_padding_for_bitshare()

    def build_placeholder_input(self):
        enonce1 = b'\xee' * self.enonce1_len
        enonce2 = b'\xdd' * self.enonce2_len
        return self.build_input(enonce1, enonce2)

    def build_input(self, enonce1, enonce2, padding=None):
        ''' enonce1, enonce2 and padding (if provided) should be byte strings '''
        script = self.script_prefix + make_push_str(enonce1 + enonce2) + self.script_postfix
        if padding is not None:
            script += padding
        return CoinbaseInput(self.height, script)

    def required_padding_for_bitshare(self):
        ''' Determines the required padding in the input script to make sure
            the length of entire txn *without* the last output & locktime is a
            multiple of 512 bits. This is required to get the coinbase midstate
            to provide to the bitshare hasher.

            For this we assume that the last output is the one added by the
            bitshare hasher and so we ignore that one.
        '''
        # build the whole thing including the last output
        placeholder_input = self.build_placeholder_input()
        cb_txn = BitshareCoinbaseTransaction(Transaction.DEFAULT_TRANSACTION_VERSION,
                                             [placeholder_input],
                                             self.outputs,
                                             self.lock_time)

        cb1_len_bits = (len(bytes(cb_txn)) - cb_txn.bitshare_output_length - 4) * 8  # 4 is lock_time length in bytes
        num_bits_padding = (512 - (cb1_len_bits % 512)) % 512
        if num_bits_padding % 8 != 0:
            raise ValueError("Required padding for coinbase input is not a multiple of 8")

        num_bytes_padding = int(num_bits_padding / 8)

        if num_bytes_padding == 0:
            padding = b''
        elif num_bytes_padding == 1:
            padding = b'\x00'
        else:
            padding = bytes([num_bytes_padding - 1]) + bytes(num_bytes_padding - 1)

        return padding

    def build(self, enonce1, enonce2, bitshare=True):
        ''' Builds a coinbase txn and returns it. If bitshare == True,
            padding is added to the coinbase input script to align the
            length of the txn without the last output & locktime to a
            512-bit boundary.

            enonce1 and enonce2 are byte strings
        '''

        if len(enonce1) != self.enonce1_len:
            raise ValueError("len(enonce1) does not match enonce1_len")
        if len(enonce2) != self.enonce2_len:
            raise ValueError("len(enonce2) does not match enonce2_len")

        padding = self.bitshare_padding if bitshare else None
        cb_input = self.build_input(enonce1, enonce2, padding)
        tx_type = BitshareCoinbaseTransaction if bitshare else Transaction

        return tx_type(Transaction.DEFAULT_TRANSACTION_VERSION,
                       [cb_input],
                       self.outputs,
                       self.lock_time)

    @property
    def bytes(self):
        pass
