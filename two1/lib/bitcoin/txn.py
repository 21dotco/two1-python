import copy
import struct

from two1.lib.bitcoin import crypto
from two1.lib.bitcoin.hash import Hash
from two1.lib.bitcoin.script import Script
from two1.lib.bitcoin.utils import bytes_to_str
from two1.lib.bitcoin.utils import pack_compact_int
from two1.lib.bitcoin.utils import pack_u32
from two1.lib.bitcoin.utils import pack_u64
from two1.lib.bitcoin.utils import pack_var_str
from two1.lib.bitcoin.utils import unpack_compact_int
from two1.lib.bitcoin.utils import unpack_u32
from two1.lib.bitcoin.utils import unpack_u64


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
            tuple: First element of the tuple is the TransactionInput
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
        height (uint): The height of the block coinbase is part of
                       will go into.  Not required for version 1
                       blocks.
        raw_script (bytes): the bytes of the coinbase script. For
                            block_version > 1 the height portion
                            should NOT be included in this script.
        sequence (int): Unless you are Satoshi with a version 1 block,
                        the default is fine. If you are Satoshi, send
                        me some of your private keys and set this to
                        0.
        block_version (int): The version of the block this coinbase is
                             a part of or will go into. If raw_script
                             already contains the height of the block,
                             this must be 1.
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
            tuple: First element of the tuple is a TransactionOutput,
                   the second is the remainder of the byte stream.
        """
        value, b0 = unpack_u64(b)
        script_len, b0 = unpack_compact_int(b0)

        return (TransactionOutput(value, Script(b0[:script_len])),
                b0[script_len:])

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
            b (bytes): byte stream containing the serialized
                 transaction output.
        """
        return pack_u64(self.value) + pack_var_str(bytes(self.script))


class UnspentTransactionOutput(object):
    """ Container class for compactly describing unspent transaction outputs.

    Args:
        transaction_hash (Hash): Hash of the transaction containing
            the unspent output.
        outpoint_index (int): Index of the output.
        value (int): Number of satoshis in the output.
        scr (Script): The scriptPubKey of the output.
        confirmations (int): Number of confirmations for the transaction.
    """

    def __init__(self, transaction_hash, outpoint_index, value, scr,
                 confirmations):
        if not isinstance(transaction_hash, Hash):
            raise TypeError("transaction_hash must be a Hash object.")
        if not isinstance(scr, Script):
            raise TypeError("scr must be a Script object.")

        self.transaction_hash = transaction_hash
        self.outpoint_index = outpoint_index
        self.value = value
        self.script = scr
        self.num_confirmations = confirmations

    @property
    def confirmed(self):
        return self.num_confirmations >= 6


class Transaction(object):
    """ See https://bitcoin.org/en/developer-reference#raw-transaction-format

    Args:
        version (int): Transaction version (should always be
            1). Endianness: host
        inputs (list(TransactionInput)): all the inputs that spend
            bitcoin.
        outputs (list(TransactionOutput)): all the outputs to which
            bitcoin is sent.
        lock_time (int): Time or a block number. Endianness: host
    """

    DEFAULT_TRANSACTION_VERSION = 1  # There are no other versions currently
    SIG_HASH_OLD = 0x00  # Acts the same as SIG_HASH_ALL
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
            tuple: First element of the tuple is the Transaction,
                   second is the remainder of the byte stream.
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

    def _get_public_key_bytes(self, private_key, compressed=True):
        # In the case of extended keys (HDPublicKey), need to get
        # the underlying key and serialize that.
        if isinstance(private_key.public_key, crypto.HDPublicKey):
            pub_key = private_key.public_key._key
        else:
            pub_key = private_key.public_key

        return private_key.public_key.compressed_bytes if compressed else bytes(pub_key)

    def sign_input(self, input_index, hash_type, private_key, sub_script,
                   redeem_script=None):
        """ Signs an input.

        Args:
            input_index (int): The index of the input to sign.
            hash_type (int): What kind of signature hash to do.
            private_key (crypto.PrivateKey): private key with which
                to sign the transaction.
            sub_script (Script): the scriptPubKey of the corresponding
                utxo being spent.
            redeem_script (Script): If sub_script is a P2SH script, a
                corresponding redeem script must be provided.
        """
        if input_index < 0 or input_index >= len(self.inputs):
            raise ValueError("Invalid input index.")

        inp = self.inputs[input_index]

        curr_script_sig = inp.script
        multisig = False
        multisig_params = None
        multisig_key_index = -1
        if sub_script.is_p2sh():
            if not redeem_script:
                raise ValueError("redeem_script must not be None if sub_script is a P2SH script.")

            if not redeem_script.is_multisig_redeem():
                raise TypeError("Signing arbitrary redeem scripts is not currently supported.")

            multisig = True
            multisig_params = redeem_script.extract_multisig_redeem_info()
            tmp_scr = redeem_script
        else:
            tmp_scr = sub_script

        tmp_script = tmp_scr.remove_op("OP_CODESEPARATOR")

        compressed = False
        if hash_type & 0x1f == self.SIG_HASH_SINGLE and len(self.inputs) > len(self.outputs):
            # This is to deal with the bug where specifying an index
            # that is out of range (wrt outputs) results in a
            # signature hash of 0x1 (little-endian)
            msg_to_sign = 0x1.to_bytes(32, 'little')
        else:
            txn_copy = self._copy_for_sig(input_index, hash_type, tmp_script)

            if multisig:
                # Determine which of the public keys this private key
                # corresponds to.
                public_keys = multisig_params['public_keys']
                pub_key_full = self._get_public_key_bytes(private_key, False)
                pub_key_comp = self._get_public_key_bytes(private_key, True)

                for i, p in enumerate(public_keys):
                    if pub_key_full == p or pub_key_comp == p:
                        multisig_key_index = i
                        break

                if multisig_key_index == -1:
                    raise ValueError(
                        "Public key derived from private key does not match any of the public keys in redeem script.")
            else:
                # Before signing we should verify that the address in the
                # sub_script corresponds to that of the private key
                script_pub_key_h160_hex = tmp_script.get_hash160()
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

            msg_to_sign = bytes(Hash.dhash(bytes(txn_copy) +
                                           pack_u32(hash_type)))

        sig = private_key.sign(msg_to_sign, False)

        if multisig:
            # For multisig, we need to determine if there are already
            # signatures and if so, where we insert this signature
            inp.script = self._do_multisig_script([dict(index=multisig_key_index,
                                                        signature=sig)],
                                                  msg_to_sign,
                                                  curr_script_sig,
                                                  redeem_script,
                                                  hash_type)
        else:
            pub_key_bytes = self._get_public_key_bytes(private_key, compressed)
            pub_key_str = pack_var_str(pub_key_bytes)
            script_sig = pack_var_str(
                sig.to_der() + pack_compact_int(hash_type)) + pub_key_str
            inp.script = Script(script_sig)

        return True

    def _do_multisig_script(self, sigs, message, current_script_sig,
                            redeem_script, hash_type):
        # If the current script is empty or None, create it
        sig_script = None
        if current_script_sig is None or not str(current_script_sig):
            sig_bytes = [s['signature'].to_der() + pack_compact_int(hash_type)
                         for s in sigs]

            sig_script = Script.build_multisig_sig(sigs=sig_bytes,
                                                   redeem_script=redeem_script)
        else:
            # Need to extract all the sigs already present
            multisig_params = redeem_script.extract_multisig_redeem_info()
            sig_info = current_script_sig.extract_multisig_sig_info()

            # Do a few quick sanity checks
            if str(sig_info['redeem_script']) != str(redeem_script):
                raise ValueError(
                    "Redeem script in signature script does not match redeem_script!")

            if len(sig_info['signatures']) == multisig_params['n']:
                # Already max number of signatures
                return current_script_sig

            # Go through the signatures and match them up to the public keys
            # in the redeem script
            pub_keys = []
            for pk in multisig_params['public_keys']:
                pub_key, _ = crypto.PublicKey.from_bytes(pk)
                pub_keys.append(pub_key)

            existing_sigs = []
            for s in sig_info['signatures']:
                s1, h = s[:-1], s[-1]  # Last byte is hash_type
                existing_sigs.append(crypto.Signature.from_der(s1))
                if h != hash_type:
                    raise ValueError("hash_type does not match that of the existing signatures.")

            # Match them up
            existing_sig_indices = self._match_sigs_to_pub_keys(existing_sigs,
                                                                pub_keys,
                                                                message)
            sig_indices = {s['index']: s['signature'] for s in sigs}

            # Make sure there are no dups
            all_indices = set(list(existing_sig_indices.keys()) + \
                              list(sig_indices.keys()))
            if len(all_indices) < len(existing_sig_indices) + len(sig_indices):
                raise ValueError("At least one signature matches an existing signature.")

            if len(all_indices) > multisig_params['n']:
                raise ValueError("There are too many signatures.")

            all_sigs = []
            for i in sorted(all_indices):
                if i in existing_sig_indices:
                    all_sigs.append(existing_sig_indices[i])
                elif i in sig_indices:
                    all_sigs.append(sig_indices[i])

            all_sigs_bytes = [s.to_der() + pack_compact_int(hash_type)
                              for s in all_sigs]
            sig_script = Script.build_multisig_sig(all_sigs_bytes,
                                                   redeem_script)

        return sig_script

    def _match_sigs_to_pub_keys(self, sigs, pub_keys, message):
        sig_indices = {}
        for sig in sigs:
            for i, pub_key in enumerate(pub_keys):
                if sig_indices[i]:
                    continue

                if pub_key.verify(message, sig, False):
                    sig_indices[i] = sig

        return sig_indices

    def __str__(self):
        """ Returns a human readable formatting of this transaction.

        Returns:
            s (str): A string containing the human readable transaction.
        """
        s = "Transaction: Version: %d, lock time: %d\nInputs:\n" % (
            self.version, self.lock_time)
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
