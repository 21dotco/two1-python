"""This submodule provides a single Script class that has knowledge of all
Bitcoin opcodes. At the simplest level, it can read in the raw bytes of a
Bitcoin script, parse it, and determine what type of script it is (P2PKH, P2SH,
multi-sig, etc). It also provides capabilities for building more complex
scripts programmatically."""
import base58
import copy
import re
import struct

from two1.bitcoin.crypto import PublicKey
from two1.bitcoin.crypto import Signature
from two1.bitcoin.exceptions import ScriptParsingError
from two1.bitcoin.utils import bytes_to_str
from two1.bitcoin.utils import hash160
from two1.bitcoin.utils import key_hash_to_address
from two1.bitcoin.utils import pack_var_str
from two1.bitcoin.utils import unpack_var_str
from two1.bitcoin.utils import render_int


class Script(object):
    """ Handles all Bitcoin script-related needs.
    Currently this means: parsing text scripts,
    assembling/disassembling and serialization/deserialization.

    If a raw byte stream is passed in, disassembly and parsing are
    deferred until required. If parsing is immediately required,
    call Script.parse() after constructing the object.

    Args:
        script (bytes or str): Either a text or byte string containing
            the script to build.
    """

    BTC_OPCODE_TABLE = {
        'OP_0':                     0x00, 'OP_FALSE':                 0x00, 'OP_PUSHDATA1':             0x4c,
        'OP_PUSHDATA2':             0x4d, 'OP_PUSHDATA4':             0x4e, 'OP_1NEGATE':               0x4f,
        'OP_1':                     0x51, 'OP_TRUE':                  0x51, 'OP_2':                     0x52,
        'OP_3':                     0x53, 'OP_4':                     0x54, 'OP_5':                     0x55,
        'OP_6':                     0x56, 'OP_7':                     0x57, 'OP_8':                     0x58,
        'OP_9':                     0x59, 'OP_10':                    0x5a, 'OP_11':                    0x5b,
        'OP_12':                    0x5c, 'OP_13':                    0x5d, 'OP_14':                    0x5e,
        'OP_15':                    0x5f, 'OP_16':                    0x60, 'OP_NOP':                   0x61,
        'OP_IF':                    0x63, 'OP_NOTIF':                 0x64, 'OP_ELSE':                  0x67,
        'OP_ENDIF':                 0x68, 'OP_VERIFY':                0x69, 'OP_RETURN':                0x6a,
        'OP_TOALTSTACK':            0x6b, 'OP_FROMALTSTACK':          0x6c, 'OP_IFDUP':                 0x73,
        'OP_DEPTH':                 0x74, 'OP_DROP':                  0x75, 'OP_DUP':                   0x76,
        'OP_NIP':                   0x77, 'OP_OVER':                  0x78, 'OP_PICK':                  0x79,
        'OP_ROLL':                  0x7a, 'OP_ROT':                   0x7b, 'OP_SWAP':                  0x7c,
        'OP_TUCK':                  0x7d, 'OP_2DROP':                 0x6d, 'OP_2DUP':                  0x6e,
        'OP_3DUP':                  0x6f, 'OP_2OVER':                 0x70, 'OP_2ROT':                  0x71,
        'OP_2SWAP':                 0x72, 'OP_SIZE':                  0x82, 'OP_EQUAL':                 0x87,
        'OP_EQUALVERIFY':           0x88, 'OP_1ADD':                  0x8b, 'OP_1SUB':                  0x8c,
        'OP_NEGATE':                0x8f, 'OP_ABS':                   0x90, 'OP_NOT':                   0x91,
        'OP_0NOTEQUAL':             0x92, 'OP_ADD':                   0x93, 'OP_SUB':                   0x94,
        'OP_BOOLAND':               0x9a, 'OP_BOOLOR':                0x9b, 'OP_NUMEQUAL':              0x9c,
        'OP_NUMEQUALVERIFY':        0x9d, 'OP_NUMNOTEQUAL':           0x9e, 'OP_LESSTHAN':              0x9f,
        'OP_GREATERTHAN':           0xa0, 'OP_LESSTHANOREQUAL':       0xa1, 'OP_GREATERTHANOREQUAL':    0xa2,
        'OP_MIN':                   0xa3, 'OP_MAX':                   0xa4, 'OP_WITHIN':                0xa5,
        'OP_RIPEMD160':             0xa6, 'OP_SHA1':                  0xa7, 'OP_SHA256':                0xa8,
        'OP_HASH160':               0xa9, 'OP_HASH256':               0xaa, 'OP_CODESEPARATOR':         0xab,
        'OP_CHECKSIG':              0xac, 'OP_CHECKSIGVERIFY':        0xad, 'OP_CHECKMULTISIG':         0xae,
        'OP_CHECKMULTISIGVERIFY':   0xaf, 'OP_CHECKLOCKTIMEVERIFY':   0xb1,
        'OP_CAT':                   0x7e, 'OP_SUBSTR':                0x7f, 'OP_LEFT':                  0x80,
        'OP_RIGHT':                 0x81, 'OP_INVERT':                0x83, 'OP_AND':                   0x84,
        'OP_OR':                    0x85, 'OP_XOR':                   0x86, 'OP_2MUL':                  0x8d,
        'OP_2DIV':                  0x8e, 'OP_MUL':                   0x95, 'OP_DIV':                   0x96,
        'OP_MOD':                   0x97, 'OP_LSHIFT':                0x98, 'OP_RSHIFT':                0x99}

    BTC_OPCODE_REV_TABLE = {v: k for k, v in BTC_OPCODE_TABLE.items()}
    _ser_dispatch_table = None

    P2SH_TESTNET_VERSION = 0xC4
    P2SH_MAINNET_VERSION = 0x05
    P2PKH_TESTNET_VERSION = 0x6F
    P2PKH_MAINNET_VERSION = 0x00

    @staticmethod
    def from_bytes(b):
        """ Deserializes a byte stream containing a script into a Script object.
        Assumes the first part contains the length of the script in bytes.

        Args:
            b (bytes): A byte-stream containing the script, with the length
              of the script in bytes prepended.

        Returns:
            (scr, b) (tuple): A tuple with the deserialized Script object and
            the remainder of the byte stream.
        """
        raw_script, b = unpack_var_str(b)

        return (Script(raw_script), b)

    @staticmethod
    def from_hex(h, size_prepended=False):
        """ Deserializes a hex-encoded string into a Script.

        Args:
            h (str): hex-encoded string, starting with the length of
                the script as a compact int.
            size_prepended (bool): Should be True if the size of the
                script has already been prepended.

        Returns:
            Script: A Script object.
        """
        b = bytes.fromhex(h)
        if not size_prepended:
            b = pack_var_str(b)
        s, _ = Script.from_bytes(b)
        return s

    @staticmethod
    def build_p2pkh(hash160_key):
        """ Builds a Pay-to-Public-Key-Hash script.

        Args:
            hash160_key (bytes): the RIPEMD-160 hash of the public key
              in internal byte order.

        Returns:
            scr (Script): a serializable Script object containing the
            p2pkh script.
        """
        return Script(['OP_DUP',
                       'OP_HASH160',
                       hash160_key,
                       'OP_EQUALVERIFY',
                       'OP_CHECKSIG'])

    @staticmethod
    def build_p2sh(hash160_key):
        """ Builds a Pay-to-Script-Hash script.

        Args:
            hash160_key (bytes): the RIPEMD-160 hash of the script in
              internal byte order.

        Returns:
            scr (Script): a serializable Script object containing the
            p2sh script.
        """

        return Script(['OP_HASH160', hash160_key, 'OP_EQUAL'])

    @staticmethod
    def build_multisig_redeem(m, pub_keys):
        """ Builds a multisig redeem script and corresponding
        Pay-to-Script-Hash script.

        Args:
            m (int): Number of signatures required. Must be <= len(pub_keys).
            pub_keys (list(bytes)): list of serialized public keys of which the
               corresponding private keys can be used to sign when redeeming.

        Returns:
            Script: The redeem script object
        """
        if m < 1 or m > len(pub_keys):
            raise ValueError("m must be > 0 and <= len(pub_keys)!")

        redeem_script = Script("OP_%d" % m)
        for p in pub_keys:
            redeem_script.append(p)

        redeem_script.append("OP_%d" % len(pub_keys))
        redeem_script.append('OP_CHECKMULTISIG')

        return redeem_script

    @staticmethod
    def build_multisig_sig(sigs, redeem_script):
        """ Builds a multisig signature script.

        This script contains the signatures in order given
        in sigs as well as the redeem script. It is not required
        to have all required signatures in sigs. However, len(sigs)
        may not be more than the max number indicated by the redeem
        script.

        Args:
            sigs (list(bytes)): A list of signatures (in DER encoding). The
                hash_type must already be appended to the byte string for each
                signature. This function will take care of the relevant data
                push operations.
            redeem_script (Script): The script used to redeem the coins.

        Returns:
            Script: A multisig signature script. Note: if len(sigs) is less
               than the minimum number required, the script will not be valid.
        """
        multisig_params = redeem_script.extract_multisig_redeem_info()

        if len(sigs) > multisig_params['n']:
            raise ValueError("Too many signatures: %d (given) > %d (max. required)." %
                             len(sigs),
                             multisig_params['n'])

        # To correct for the early bitcoin-core off-by-1 error.
        scr = Script('OP_0')

        for s in sigs:
            scr.append(s)

        scr.append(bytes(redeem_script))

        return scr

    @staticmethod
    def build_push_int(i):
        """ Creates a script to push i onto the stack using the least possible
        number of bytes.

        Args:
            i (int): integer to be pushed onto the stack.

        Returns:
            b (bytes): Serialized bytes containing the appropriate PUSHDATA
            op for i.
        """

        if i >= 0 and i <= 16:
            return bytes(Script('OP_%d' % i))
        else:
            return bytes(Script([render_int(i)]))

    @staticmethod
    def validate_template(script, template):
        """ Validates a script against a template.

        Args:
            script (Script): A Script object.
            template (list): A list of OPs or types against which to
                validate script.

        Returns:
            bool: True if script has the same OPs and types as template,
                False otherwise.
        """
        if len(script) != len(template):
            return False

        for i, e in enumerate(template):
            if isinstance(e, str):
                if script[i] != e:
                    return False
            elif isinstance(e, type):
                if type(script[i]) != e:
                    return False

        return True

    def __init__(self, script=""):
        self._ast = []
        self._tokens = []
        self._raw_script = None

        if isinstance(script, bytes):
            self._raw_script = script
        elif isinstance(script, str):
            self._tokenize(script)
            self._parse()
        elif isinstance(script, list):
            self._tokens = script
            self._validate_tokens()
            self._parse()
        else:
            raise TypeError(
                "script must be of type 'bytes', 'str' or 'list', not %r." %
                (type(script)))

    def _check_valid_opcode(self, opcode):
        rv = True
        if isinstance(opcode, str):
            # Make sure it's a valid opcode
            if opcode not in self.BTC_OPCODE_TABLE and \
               not opcode.startswith("0x") or \
               opcode in ['OP_PUSHDATA1', 'OP_PUSHDATA2', 'OP_PUSHDATA3']:
                rv = False

        return rv

    def _check_tokenized(self):
        if not self._tokens:
            if self._raw_script:
                self._disassemble()
                self._parse()
                self._raw_script = None
            else:
                # Empty script, so just set _tokens to empty list
                self._tokens = []

    def __getitem__(self, key):
        self._check_tokenized()
        return self._tokens[key]

    def __setitem__(self, key, value):
        self._check_tokenized()

        if not isinstance(value, str) and \
           not isinstance(value, bytes):
            raise TypeError("value must either be str or bytes.")

        v = value
        if not self._check_valid_opcode(value):
            raise ValueError("%s is not a valid opcode" % value)
        if isinstance(value, str) and value.startswith("0x"):
            v = bytes.fromhex(value[2:])

        self._tokens[key] = v
        self._parse()

    def __delitem__(self, key):
        self._check_tokenized()
        del self._tokens[key]
        self._parse()

    def __iter__(self):
        self._check_tokenized()
        return iter(self._tokens)

    def __len__(self):
        self._check_tokenized()
        return len(self._tokens)

    def insert(self, index, value):
        """ Inserts an OP before the specified index

        Args:
            index (int): Index of element to insert before
            value (str or bytes): OP to insert.
        """
        v = value
        if not self._check_valid_opcode(value):
            raise ValueError("%s is not a valid opcode" % value)
        if isinstance(value, str) and value.startswith("0x"):
            v = bytes.fromhex(value[2:])

        self._check_tokenized()

        self._tokens.insert(index, v)
        self._parse()

    def append(self, value):
        """ Append an OP to the end of the script

        Args:
            value (str or bytes): OP to insert.
        """
        v = value
        if not self._check_valid_opcode(value):
            raise ValueError("%s is not a valid opcode" % value)
        if isinstance(value, str) and value.startswith("0x"):
            v = bytes.fromhex(value[2:])

        self._check_tokenized()

        self._tokens.append(v)
        self._parse()

    @property
    def ast(self):
        """ Returns the script's abstract syntax tree.

        Returns:
            list: a nested list of opcodes which follow the flow of a script's
                conditional if/else branching.
        """
        if not self._ast:
            self._parse()

        return self._ast

    def hash160(self):
        """ Return the RIPEMD-160 hash of the SHA-256 hash of the
        script.

        Returns:
            bytes: RIPEMD-160 byte string.
        """
        return hash160(bytes(self))

    def address(self, testnet=False):
        """ Returns the Base58Check encoded version of the HASH160.

        Args:
            testnet (bool): Whether or not the key is intended for testnet
               usage. False indicates mainnet usage.

        Returns:
            bytes: Base58Check encoded string
        """
        rv = ""
        prefix = bytes([self.P2SH_TESTNET_VERSION if testnet else self.P2SH_MAINNET_VERSION])
        rv = base58.b58encode_check(prefix + self.hash160())

        return rv

    def extract_sig_info(self):
        """ Returns the signature and corresponding public key.

        Returns:
            dict: Contains three keys:
                'hash_type': Integer
                'signature': The DER-encoded signature
                'public_key': The bytes corresponding the public key.
        """
        if len(self) != 2:
            raise TypeError("Script is not a P2PKH signature script")

        if not isinstance(self[0], bytes) or \
           not isinstance(self[1], bytes):
            raise TypeError(
                "Signature script must contain two push operations.")

        try:
            sig_bytes = self[0]
            hash_type = sig_bytes[-1]
            _ = Signature.from_der(sig_bytes[:-1])
        except ValueError:
            raise TypeError("Signature does not appear to be valid")

        try:
            _ = PublicKey.from_bytes(self[1])
        except ValueError:
            raise TypeError("Public key does not appear to be valid")

        return dict(hash_type=hash_type,
                    signature=sig_bytes,
                    public_key=self[1])

    def extract_multisig_redeem_info(self):
        """ Returns information about the multisig redeem script

        Returns:
            dict: Contains the following list of keys:
               'm' (int): Required number of signatures.
               'n' (int): Maximum number of signatures.
               'public_keys' (list): List of byte strings corresponding to public keys.
        """
        exc = TypeError("This script is not a multisig redeem script.")

        # The last byte of the raw script should be 0xae which is
        # OP_CHECKMULTISIG
        scr_bytes = bytes(self)

        if scr_bytes[-1] != self.BTC_OPCODE_TABLE['OP_CHECKMULTISIG']:
            raise exc

        # Check m and n to be sure they are valid
        m = scr_bytes[0] - 0x50
        n = scr_bytes[-2] - 0x50

        if m <= 0 or m >= 16:
            raise exc

        if n < m or n >= 16:
            raise exc

        # Now consume all the public keys and make sure those were
        # the only things in.
        b = scr_bytes[1:]
        public_keys = []
        for i in range(n):
            pk, b = unpack_var_str(b)
            public_keys.append(pk)
            # May want to do additional checking to make
            # sure it's a public key in the future.

        # Should only be 2 bytes left
        if len(b) != 2:
            raise exc
        if (b[0] - 0x50) != n or \
           b[1] != self.BTC_OPCODE_TABLE['OP_CHECKMULTISIG']:
            raise exc

        return dict(m=m, n=n, public_keys=public_keys)

    def extract_multisig_sig_info(self):
        """ Returns information about a multisig signature script.

        Returns:
            dict: With the following key/value pairs:
                'signatures' (list): List of DER-encoded signatures with hash_type appended at the end of the byte string.
                'redeem_script' (Script): The associated redeem script.
        """
        # A signature script should start with OP_0
        if self[0] != 'OP_0':
            raise TypeError("Script does not start with OP_0!")

        # Everything after OP_0 and before the last operand is a signature.
        # If it does not start with '0x', something is wrong.
        sigs = []
        for i, x in enumerate(self[1:-1]):
            if isinstance(x, bytes):
                sigs.append(x)
            else:
                raise TypeError(
                    "Operand %d does not seem to be a signature!" % i)

        # The last operand should be the redeem script
        redeem_script = Script(self[-1])

        if not redeem_script.is_multisig_redeem():
            raise TypeError("Invalid or no redeem script found!")

        return dict(signatures=sigs, redeem_script=redeem_script)

    def is_p2pkh(self):
        """ Returns whether this script is a common Pay-to-Public-Key-Hash
        script.

        Returns:
            bool: True if it is a common P2PKH script, False otherwise.
        """
        scr_str = str(self)
        p2pkh_re = "^OP_DUP OP_HASH160 0x([0-9a-fA-F]{2}){20} OP_EQUALVERIFY OP_CHECKSIG$"
        m = re.search(p2pkh_re, scr_str)

        return bool(m)

    def is_p2sh(self):
        """ Returns whether this script is a Pay-to-Script-Hash
        script.

        Returns:
            bool: True if it is a P2SH script, False otherwise.
        """
        scr_str = str(self)
        p2sh_re = "^OP_HASH160 0x([0-9a-fA-F]{2}){20} OP_EQUAL$"
        m = re.search(p2sh_re, scr_str)

        return bool(m)

    def is_p2pkh_sig(self):
        """ Returns whether this script a Pay-to-Public-Key-Hash
        signature script.

        Returns:
            bool: True if it is a P2PKH signature script, False otherwise.
        """
        try:
            self.extract_sig_info()
            return True
        except TypeError:
            return False

    def is_multisig_redeem(self):
        """ Returns whether this script is a multi-sig redeem script.

        Returns:
            bool: True if it is a multi-sig redeem script, False otherwise.
        """
        try:
            self.extract_multisig_redeem_info()
            return True
        except TypeError:
            return False

    def is_multisig_sig(self):
        """ Returns whether this script is a multi-sig signature script.

        Returns:
            bool: True if it is a multi-sig signature script, False otherwise.
        """
        try:
            self.extract_multisig_sig_info()
            return True
        except TypeError:
            return False

    def get_hash160(self):
        """ Scans the script for OP_HASH160 and returns the data
        immediately following it.

        Returns:
            bytes: the hash160 or None.
        """
        self._check_tokenized()
        if not self._tokens:
            raise ScriptParsingError(
                "Script is empty or has not been disassembled")

        # Scan for OP_HASH160
        for i, opcode in enumerate(self):
            if opcode == "OP_HASH160":
                return self[i+1]

        return None

    def get_addresses(self, testnet=False):
        """ Returns all addresses found in this script

        For output scripts, P2PKH scripts will return a single
        address the funds are being sent to. P2SH scripts will
        return a single address of the script the funds are being
        sent to.

        For input scripts, only standard signature and
        multi-signature scripts will return results: the
        address(es) used to sign. For standard signature scripts,
        a single address is returned while for multi-sig scripts,
        all n addresses in the redeem script are returned.

        Args:
            testnet (bool): True if the addresses are being used on testnet,
                False if used on mainnet.

        Returns:
            list: A list of Base58Check encoded bitcoin addresses.
        """
        rv = []
        # Determine script type
        if self.is_p2pkh():
            version = self.P2PKH_TESTNET_VERSION if testnet else self.P2PKH_MAINNET_VERSION
            rv.append(key_hash_to_address(self.get_hash160(), version))
        elif self.is_p2sh():
            version = self.P2SH_TESTNET_VERSION if testnet else self.P2SH_MAINNET_VERSION
            rv.append(key_hash_to_address(self.get_hash160(), version))
        elif self.is_multisig_sig():
            # Extract out the info
            version = self.P2PKH_TESTNET_VERSION if testnet else self.P2PKH_MAINNET_VERSION
            sig_info = self.extract_multisig_sig_info()
            redeem_info = sig_info['redeem_script'].extract_multisig_redeem_info()
            for p in redeem_info['public_keys']:
                rv.append(key_hash_to_address(hash160(p), version))
            # Also include the address of the redeem script itself.
            redeem_version = self.P2SH_TESTNET_VERSION if testnet else self.P2SH_MAINNET_VERSION
            rv.append(key_hash_to_address(sig_info['redeem_script'].hash160(), redeem_version))
        elif self.is_p2pkh_sig():
            version = self.P2PKH_TESTNET_VERSION if testnet else self.P2PKH_MAINNET_VERSION
            # Normal signature script...
            sig_info = self.extract_sig_info()
            rv.append(key_hash_to_address(hash160(sig_info['public_key']),
                                          version))
        elif Script.validate_template(self, [bytes, 'OP_CHECKSIG']):
            version = self.P2PKH_TESTNET_VERSION if testnet else self.P2PKH_MAINNET_VERSION
            rv.append(key_hash_to_address(hash160(self[0]), version))

        return rv

    def remove_op(self, op):
        """ Returns a new script without any OP_<op>'s in it.

        Returns:
            scr (Script): New script object devoid of any OP_<op>.
        """
        self._check_tokenized()
        if op not in self.BTC_OPCODE_TABLE:
            raise ValueError("Unknown op (%s)" % (op))

        return Script([t for t in self._tokens if t != op])

    def _validate_tokens(self):
        """ Checks that there are no push OPs in the tokens as they
            should all just be bytes.
        """
        self._check_tokenized()
        for t in self._tokens:
            if t in ['OP_PUSHDATA1', 'OP_PUSHDATA2', 'OP_PUSHDATA3']:
                raise TypeError(
                    "No push ops allowed, simply add the bytes to be pushed.")

    def _tokenize(self, s):
        """ Breaks up a string into tokens and converts all tokens
            starting with "0x" into bytes
        """
        self._tokens = [bytes.fromhex(t[2:]) if t.startswith("0x") else t
                        for t in s.split()]
        self._validate_tokens()

    def _parse(self):
        """ This is a basic Recursive Descent Parser for the Bitcoin
            script language. It will tokenize the input script to allow
            interpretation of that script. The resultant tokens are stored
            in ``self._ast``.
        """
        self._check_tokenized()
        if self._tokens:
            self._temp_tokens = copy.deepcopy(self._tokens)
            self._ast = self._do_parse()

    def _do_parse(self, in_if_else=False):
        if_clause = None
        else_clause = None
        ast = []
        while self._temp_tokens:
            opcode = self._temp_tokens.pop(0)
            if opcode in ['OP_0', 'OP_FALSE']:
                ast.append(opcode)
            elif isinstance(opcode, bytes):
                l = len(opcode)
                if l <= 0x4b:
                    ast.append(opcode)
                elif l <= 0xff:
                    ast.append(['OP_PUSHDATA1', bytes([l]), opcode])
                elif l <= 0xffff:
                    ast.append(['OP_PUSHDATA2', struct.pack("<H", l), opcode])
                elif l <= 0xffffffff:
                    ast.append(['OP_PUSHDATA4', struct.pack("<I", l), opcode])
            elif opcode in ['OP_PUSHDATA1', 'OP_PUSHDATA2', 'OP_PUSHDATA4']:
                raise TypeError(
                    "No push ops allowed, simply add the bytes to be pushed.")
            elif opcode in ['OP_IF', 'OP_NOTIF']:
                got_endif = False
                # Recursively descend
                if_clause = self._do_parse(True)
                if if_clause[-1] == 'OP_ENDIF':
                    got_endif = True
                    if_clause.pop()

                token = [opcode, if_clause]

                # Check for an else clause
                if self._temp_tokens and \
                   self._temp_tokens[0] == 'OP_ELSE':
                    self._temp_tokens.pop(0)
                    else_clause = self._do_parse(True)
                    if else_clause[-1] == 'OP_ENDIF':
                        got_endif = True
                        else_clause.pop()
                    token.append(else_clause)

                if got_endif:
                    token.append('OP_ENDIF')
                else:
                    raise ScriptParsingError("No matching OP_ENDIF")
                ast.append(token)
            elif opcode in ['OP_ELSE', 'OP_ENDIF']:
                if not in_if_else:
                    raise ScriptParsingError("Illegal %s when not in if/else." %
                                             opcode)

                if opcode == 'OP_ELSE':
                    self._temp_tokens = [opcode] + self._temp_tokens
                else:
                    ast.append(opcode)

                break
            else:
                # Everything else can just be put on as a normal token
                ast.append(opcode)

        return ast

    def _disassemble(self):
        """ Disassembles a raw script (in bytes) to human-readable text
            using the opcodes in BTC_OPCODE_TABLE. The disassembled string
            is stored in self._tokens.
        """
        if self._raw_script is None:
            return

        raw = self._raw_script

        self._tokens = []
        while raw:
            op, raw = raw[0], raw[1:]
            if op == 0x00:
                self._tokens.append('OP_0')
            elif op < 0x4b:
                self._tokens.append(raw[0:op])
                raw = raw[op:]
            else:
                opcode = Script.BTC_OPCODE_REV_TABLE[op]
                if opcode in ['OP_PUSHDATA1', 'OP_PUSHDATA2', 'OP_PUSHDATA4']:
                    pushlen = int(opcode[-1])
                    datalen = 0
                    if pushlen == 1:
                        datalen = raw[0]
                        datalen_bytes, raw = bytes([raw[0]]), raw[1:]
                    elif pushlen == 2:
                        datalen_bytes, raw = raw[0:2], raw[2:]
                        datalen = struct.unpack("<H", datalen_bytes)[0]
                    elif pushlen == 4:
                        datalen_bytes, raw = raw[0:4], raw[4:]
                        datalen = struct.unpack("<I", datalen_bytes)[0]

                    self._tokens.append(raw[:datalen])
                    raw = raw[datalen:]
                else:
                    self._tokens.append(opcode)

    def __str__(self):
        """ Creates a human-readable string representation of the script.

        Returns:
            s (str): String representation of the script
        """
        script = ""
        self._check_tokenized()
        for t in self._tokens:
            if isinstance(t, bytes):
                script += "0x%s " % bytes_to_str(t)
            else:
                script += t + " "

        return script.rstrip()

    def __bytes__(self):
        """ Serializes the object into a byte stream.
        It does *not* prepend the length of the script to the returned
        bytes. To do so, call two1.bitcoin.utils.pack_var_str() passing
        in the returned bytes.

        Returns:
            b (bytes): a serialized byte stream of this Script object.
        """
        b = b''
        i = 0
        if self._raw_script is not None:
            return self._raw_script

        while i < len(self):
            t = self[i]
            if isinstance(t, bytes):
                l = len(t)
                if l < 0x01:
                    raise ValueError(
                        "Empty byte string not allowed.")
                elif l <= 0x4b:
                    b += bytes([l])
                    b += t
                else:
                    if l <= 0xff:
                        op = 'OP_PUSHDATA1'
                        pushlen = bytes([l])
                    elif l <= 0xffff:
                        op = 'OP_PUSHDATA2'
                        pushlen = struct.pack("<H", l)
                    elif l <= 0xffffffff:
                        op = 'OP_PUSHDATA4'
                        pushlen = struct.pack("<I", l)
                    else:
                        raise ValueError(
                            "op has too much data to push onto stack.")

                    b += bytes([self.BTC_OPCODE_TABLE[op]])
                    b += pushlen
                    b += t
            else:
                b += bytes([self.BTC_OPCODE_TABLE[t]])

            i += 1

        return b

    def to_hex(self):
        """ Generates a hex encoding of the serialized script.

        Returns:
            str: Hex-encoded serialization.
        """
        return bytes_to_str(bytes(self))
