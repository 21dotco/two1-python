import copy
import hashlib
import struct

from two1.lib.bitcoin import crypto
from two1.lib.bitcoin.hash import Hash
from two1.lib.bitcoin.script import Script
from two1.lib.bitcoin.utils import address_to_key_hash
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

    def get_addresses(self, testnet=False):
        """ Returns all addresses associated with the script in this input.

        Args:
            testnet (bool): True if the transaction is a testnet transaction.

        Returns:
            list (str): A list of all addresses found in the script.
        """
        return self.script.get_addresses(testnet)

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
            scr = Script.build_push_int(self.height) + raw_script

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

    def get_addresses(self, testnet=False):
        """ Returns all addresses associated with the script in this output.

        Args:
            testnet (bool): True if the transaction is a testnet transaction.

        Returns:
            list (str): A list of all addresses found in the script.
        """
        return self.script.get_addresses(testnet)

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

    @staticmethod
    def from_hex(h):
        """ Deserializes a hex-ecnoded string into a Transaction.

        Args:
            h (str): hex-encoded string starting with the version.

        Returns:
            Transaction: the deserialized Transaction object.
        """
        tx, _ = Transaction.from_bytes(bytes.fromhex(h))
        return tx

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

    def sign_input(self, input_index, hash_type, private_key, sub_script):
        """ Signs an input.

        Args:
            input_index (int): The index of the input to sign.
            hash_type (int): What kind of signature hash to do.
            private_key (crypto.PrivateKey): private key with which
                to sign the transaction.
            sub_script (Script): the scriptPubKey of the corresponding
                utxo being spent if the outpoint is P2PKH or the redeem
                script if the outpoint is P2SH.
        """
        if input_index < 0 or input_index >= len(self.inputs):
            raise ValueError("Invalid input index.")

        inp = self.inputs[input_index]

        curr_script_sig = inp.script
        multisig = False
        multisig_params = None
        multisig_key_index = -1
        if sub_script.is_multisig_redeem():
            multisig = True
            multisig_params = sub_script.extract_multisig_redeem_info()
        elif not sub_script.is_p2pkh():
            raise TypeError("Signing arbitrary redeem scripts is not currently supported.")

        tmp_script = sub_script.remove_op("OP_CODESEPARATOR")

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
                                                  tmp_script,
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
                pub_keys.append(crypto.PublicKey.from_bytes(pk))

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
                if i in sig_indices:
                    continue

                if pub_key.verify(message, sig, False):
                    sig_indices[i] = sig

        return sig_indices

    def verify_input_signature(self, input_index, sub_script):
        """ Verifies the signature for an input.

            This also confirms that the HASH160 in the provided sub_script
            corresponds with that found in the input sigScript.

        Args:
            input_index (int): The index of the input to verify.
            sub_script (Script): The P2SH script in the corresponding outpoint.

        Returns:
            bool: True if the sigScript is verified, False otherwise.
        """
        # First extract the signature script
        sig_script = self.inputs[input_index].script

        # Both of these will eventually get replaced with a generic
        # script interpreter & verifier.
        rv = False
        if sig_script.is_multisig_sig():
            rv = self._verify_p2sh_multisig_input(input_index, sub_script)
        elif sub_script.is_p2pkh():
            rv = self._verify_p2pkh_input(input_index, sub_script)

        return rv

    def verify_partial_multisig(self, input_index, sub_script):
        """ Verifies a partially signed multi-sig input.

            This also confirms that the HASH160 in the provided sub_script
            corresponds with that found in the input sigScript.

        Args:
            input_index (int): The index of the input to verify.
            sub_script (Script): The P2SH script in the corresponding outpoint.

        Returns:
            bool: True if > 1 and <= m signatures verify the input.
        """
        return self._verify_p2sh_multisig_input(input_index, sub_script, True)

    def _verify_p2pkh_input(self, input_index, sub_script):
        if not sub_script.is_p2pkh():
            raise TypeError("sub_script is not a P2PKH script!")

        rv = False
        sig_script = self.inputs[input_index].script

        # Use a fake stack
        stack = []

        # Push sigScript and publicKey onto stack
        stack.append(bytes.fromhex(sig_script.ast[0][2:]))
        stack.append(bytes.fromhex(sig_script.ast[1][2:]))

        # OP_DUP
        stack.append(stack[-1])

        # OP_HASH160
        pub_key_bytes = stack.pop()
        pub_key = crypto.PublicKey.from_bytes(pub_key_bytes)
        # Was it compressed?
        compressed = pub_key_bytes[0] in [0x02, 0x03]
        hash160 = pub_key.hash160(compressed=compressed)

        # OP_EQUALVERIFY - this pub key must match the one in
        # sub_script
        sub_script_pub_key_hash = bytes.fromhex(sub_script.get_hash160()[2:])
        rv = hash160 == sub_script_pub_key_hash

        # OP_CHECKSIG
        stack.pop()  # pop duplicate pub key off stack
        script_sig_complete = stack.pop()
        script_sig, hash_type = script_sig_complete[:-1], script_sig_complete[-1]

        # Re-create txn for sig verification
        txn_copy_bytes = bytes(self._copy_for_sig(input_index,
                                                  hash_type,
                                                  sub_script))

        # Now verify
        sig = crypto.Signature.from_der(script_sig)
        msg = txn_copy_bytes + pack_u32(hash_type)
        tx_digest = hashlib.sha256(msg).digest()
        rv &= pub_key.verify(tx_digest, sig)

        return rv

    def _verify_p2sh_multisig_input(self, input_index, sub_script,
                                    partial=False):
        if not sub_script.is_p2sh():
            raise TypeError("sub_script is not a P2SH script!")

        rv = False
        sig_script = self.inputs[input_index].script

        if not sig_script.is_multisig_sig():
            raise TypeError("sigScript doesn't appear to be a multisig signature script")

        stack = []
        sig_info = sig_script.extract_multisig_sig_info()

        stack.append(bytes([Script.BTC_OPCODE_TABLE[sig_script.ast[0]]]))  # Push OP_0

        # Push all the signatures
        hash_types = set()
        for s in sig_info['signatures']:
            s1, hash_type = s[:-1], s[-1]
            stack.append(s1)
            hash_types.add(hash_type)

        if len(hash_types) != 1:
            raise TypeError("Not all signatures have the same hash type!")

        hash_type = hash_types.pop()
        redeem_script = sig_info['redeem_script']
        redeem_script_h160 = redeem_script.hash160()

        # Re-create txn for sig verification
        txn_copy_bytes = bytes(self._copy_for_sig(input_index,
                                                  hash_type,
                                                  redeem_script))
        msg = txn_copy_bytes + pack_u32(hash_type)
        txn_digest = hashlib.sha256(msg).digest()

        sub_script_h160 = bytes.fromhex(sub_script.get_hash160()[2:])
        rv = redeem_script_h160 == sub_script_h160

        rs_info = redeem_script.extract_multisig_redeem_info()
        # Now start pushing the elements of the redeem script
        stack.append(bytes([0x50 + rs_info['m']]))
        for p in rs_info['public_keys']:
            stack.append(p)
        stack.append(bytes([0x50 + rs_info['n']]))

        try:
            res, match_count = self._op_checkmultisig(stack=stack,
                                                      txn_digest=txn_digest,
                                                      partial=partial)
            if partial:
                rv &= match_count > 0 and match_count <= len(sig_info['signatures'])
            else:
                rv &= res
        except Exception as e:
            rv = False

        return rv

    def _op_checkmultisig(self, stack, txn_digest, partial=False):
        # This belongs in Script, and will get moved later
        num_keys = int.from_bytes(stack.pop(), byteorder='big') - 0x50
        keys_bytes = []
        for i in range(num_keys):
            keys_bytes.insert(0, stack.pop())
        public_keys = [crypto.PublicKey.from_bytes(p) for p in keys_bytes]

        min_num_sigs = int.from_bytes(stack.pop(), byteorder='big') - 0x50

        # Although "m" is the *minimum* number of required signatures, bitcoin
        # core only consumes "m" signatures and then expects an OP_0. This
        # means that if m < min_num_sigs <= n, bitcoin core will return a
        # script failure. See:
        # https://github.com/bitcoin/bitcoin/blob/0.10/src/script/interpreter.cpp#L840
        # We will do the same.
        sigs = []
        for i in range(min_num_sigs):
            s = stack.pop()
            try:
                sig = crypto.Signature.from_der(s)
                sigs.insert(0, sig)
            except ValueError:
                if partial:
                    # Put it back on stack
                    stack.append(s)
                else:
                    # If not a partial evaluation there are not enough
                    # sigs
                    rv = False
                break

        # Now we verify
        last_match = -1
        rv = True
        match_count = 0
        for sig in sigs:
            matched_any = False
            for i, pub_key in enumerate(public_keys[last_match+1:]):
                if pub_key.verify(txn_digest, sig):
                    last_match = i
                    match_count += 1
                    matched_any = True
                    break

            if not matched_any:
                # Bail early if the sig couldn't be verified
                # by any public key
                rv = False
                break

        rv &= match_count >= min_num_sigs

        # Now make sure the last thing on the stack is OP_0
        rv &= stack.pop() == bytes([0])
        rv &= len(stack) == 0

        return rv, match_count

    def output_index_for_address(self, address_or_hash160):
        """ Returns the index of the output in this transaction
            that pays to the provided address.

        Args:
            address_or_hash160 (str or bytes): If a string, a
                Base58Check encoded address. If bytes, the hash160
                of the public key.

        Returns:
            int: The index of the corresponding output or None.
        """
        if isinstance(address_or_hash160, str):
            ver, h160_bytes = address_to_key_hash(address_or_hash160)
            h160 = bytes_to_str(h160_bytes)
        elif isinstance(address_or_hash160, bytes):
            h160 = bytes_to_str(address_or_hash160)
        else:
            raise TypeError("address_or_hash160 can only be bytes or str")

        rv = None
        for i, o in enumerate(self.outputs):
            scr = o.script
            if scr.is_p2pkh() or scr.is_p2sh():
                if scr.get_hash160()[2:] == h160:
                    rv = i
                    break

        return rv

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

    def to_hex(self):
        """ Generates a hex encoding of the serialized transaction.

        Returns:
            str: Hex-encoded serialization.
        """
        return bytes_to_str(bytes(self))

    def get_addresses(self, testnet=False):
        """ Returns all addresses associated with this transaction.

        Args:
            testnet (bool): True if the transaction is a testnet transaction.

        Returns:
            dict: A dict containing the following key/value pairs:
                'inputs': list of lists of addresses, one per input
                'outputs': list of lists of addresses, one per output
        """
        input_addresses = []
        output_addresses = []
        for i in self.inputs:
            input_addresses.append(i.get_addresses(testnet))

        for o in self.outputs:
            output_addresses.append(o.get_addresses(testnet))

        return dict(inputs=input_addresses,
                    outputs=output_addresses)
