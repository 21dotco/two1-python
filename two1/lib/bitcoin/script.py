import base58
import hashlib
import re
import struct

from two1.lib.bitcoin.crypto import PublicKey
from two1.lib.bitcoin.crypto import Signature
from two1.lib.bitcoin.exceptions import ParsingError
from two1.lib.bitcoin.utils import bytes_to_str
from two1.lib.bitcoin.utils import hash160
from two1.lib.bitcoin.utils import key_hash_to_address
from two1.lib.bitcoin.utils import pack_var_str
from two1.lib.bitcoin.utils import unpack_var_str
from two1.lib.bitcoin.utils import render_int


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
        'OP_CHECKMULTISIGVERIFY':   0xaf, }

    BTC_OPCODE_REV_TABLE = {v: k for k, v in BTC_OPCODE_TABLE.items()}
    _ser_dispatch_table = None

    P2SH_TESTNET_VERSION = 0xC4
    P2SH_MAINNET_VERSION = 0x05
    P2PKH_TESTNET_VERSION = 0x6F
    P2PKH_MAINNET_VERSION = 0x00

    @classmethod
    def _walk_ast(cls, ast, dispatch_table, default_handler=None, data=None):
        for a in ast:
            opcode = None
            args = None
            if type(a) is list:
                opcode = a[0]
                args = a[1:]
            else:
                opcode = a

            handler = dispatch_table.get(opcode, default_handler)
            if handler is not None:
                data = handler(opcode, args, data)
            else:
                raise ValueError("Opcode %s has no entry in the given dispatch_table!" % opcode)

        return data

    @classmethod
    def _serialize_pushdata(cls, opcode, args, bytestr):
        pushlen = int(opcode[-1])

        if len(args) < 2:
            raise ValueError("Not enough arguments for %s" % opcode)

        datalen = int(args[0], 0)
        pushdata = args[1]

        bytestr += bytes([cls.BTC_OPCODE_TABLE[opcode]])

        if pushlen == 1:
            bytestr += bytes([datalen])
        elif pushlen == 2:
            bytestr += struct.pack("<H", datalen)
        elif pushlen == 4:
            bytestr += struct.pack("<I", datalen)

        bytestr += bytes.fromhex(pushdata[2:])
        return bytestr

    @classmethod
    def _serialize_var_data(cls, opcode, args, bytestr):
        data = bytes.fromhex(opcode[2:])
        if len(data) < 0x01 or len(data) > 0x4b:
            raise ValueError("Opcode has too much data to push onto stack: \"%s\"" % opcode)
        bytestr += bytes([len(data)])
        bytestr += data

        return bytestr

    @classmethod
    def _serialize_if_else(cls, opcode, args, bytestr):
        bytestr += bytes([cls.BTC_OPCODE_TABLE[opcode]])

        if len(args) == 0:
            raise ValueError("Not enough clauses for %s!" % opcode)

        bytestr += cls._walk_ast(args[0],
                                 cls._ser_dispatch_table,
                                 cls._serialize_var_data,
                                 b'')

        if len(args) == 2:
            bytestr += bytes([cls.BTC_OPCODE_TABLE['OP_ELSE']])
            bytestr += cls._walk_ast(args[1],
                                     cls._ser_dispatch_table,
                                     cls._serialize_var_data,
                                     b'')
            bytestr += bytes([cls.BTC_OPCODE_TABLE['OP_ENDIF']])

        return bytestr

    @classmethod
    def _serialize_default_opcode(cls, opcode, args, bytestr):
        bytestr += bytes([cls.BTC_OPCODE_TABLE[opcode]])

        return bytestr

    @classmethod
    def _build_serializer_dispatch_table(cls):
        table = {}
        for k, v in cls.BTC_OPCODE_TABLE.items():
            if k in ['OP_PUSHDATA1', 'OP_PUSHDATA2', 'OP_PUSHDATA4']:
                table[k] = cls._serialize_pushdata
            elif k in ['OP_IF', 'OP_NOTIF']:
                table[k] = cls._serialize_if_else
            else:
                table[k] = cls._serialize_default_opcode

        cls._ser_dispatch_table = table

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
    def build_p2pkh(hash160_key):
        """ Builds a Pay-to-Public-Key-Hash script.

        Args:
            hash160_key (bytes): the RIPEMD-160 hash of the public key
                in internal byte order.

        Returns:
            scr (Script): a serializable Script object containing the
                p2pkh script.
        """
        return Script('OP_DUP OP_HASH160 0x%s OP_EQUALVERIFY OP_CHECKSIG' %
                      bytes_to_str(hash160_key))

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

        return Script('OP_HASH160 0x%s OP_EQUAL' % bytes_to_str(hash160_key))

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

        raw_redeem_script = bytes([0x50 + m])
        for p in pub_keys:
            raw_redeem_script += bytes([len(p)]) + p

        raw_redeem_script += bytes([0x50 + len(pub_keys)])
        raw_redeem_script += bytes([Script.BTC_OPCODE_TABLE['OP_CHECKMULTISIG']])

        return Script(raw_redeem_script)

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
        scr = bytes([0x00])

        for s in sigs:
            scr += pack_var_str(s)

        scr += Script.build_push_str(bytes(redeem_script))

        return Script(scr)

    @staticmethod
    def build_push_str(s):
        """ Creates a script to push s onto the stack.

        Args:
            s (bytes): bytes to be pushed onto the stack.

        Returns:
            b (bytes): Serialized bytes containing the appropriate PUSHDATA
                       op for s.
        """
        ls = len(s)
        hexstr = bytes_to_str(s)
        pd_index = 0

        if ls < Script.BTC_OPCODE_TABLE['OP_PUSHDATA1']:
            return bytes([ls]) + s
        # Determine how many bytes are required for the length
        elif ls < 0xff:
            pd_index = 1
        elif ls < 0xffff:
            pd_index = 2
        else:
            pd_index = 4

        p = bytes([Script.BTC_OPCODE_TABLE['OP_PUSHDATA%d' % (pd_index)]])
        p += bytes([ls]) + s
        return p

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
            return Script.build_push_str(render_int(i))

    def __init__(self, script=""):
        if Script._ser_dispatch_table is None:
            Script._build_serializer_dispatch_table()
        if isinstance(script, bytes):
            raw = True
        elif isinstance(script, str):
            raw = False
        else:
            raise TypeError("Script must either be of type 'bytes' or 'str', not %r." % (type(script)))

        self.script = None
        self.raw_script = None
        self._ast = []

        if raw:
            self.raw_script = script
        else:
            self.script = script
            self._parse()

    @property
    def ast(self):
        if not self._ast:
            self._parse()

        return self._ast

    def hash160(self):
        """ Return the RIPEMD-160 hash of the SHA-256 hash of a
            multisig redeem script.

        Returns
            bytes: RIPEMD-160 byte string or b"" if this script
                is not a multisig redeem script.
        """
        rv = b""
        if self.is_multisig_redeem():
            rv = hash160(bytes(self))

        return rv

    def address(self, testnet=False):
        """ Returns the Base58Check encoded version of the HASH160.

        Args:
            testnet (bool): Whether or not the key is intended for testnet
               usage. False indicates mainnet usage.

        Returns:
            bytes: Base58Check encoded string
        """
        hash160 = self.hash160()
        rv = ""
        if hash160:
            prefix = bytes([self.P2SH_TESTNET_VERSION if testnet else self.P2SH_MAINNET_VERSION])
            rv = base58.b58encode_check(prefix + hash160)

        return rv

    def extract_sig_info(self):
        """ Returns the signature and corresponding public key.

        Returns:
            dict: Contains three keys:
                'hash_type': Integer
                'signature': The DER-encoded signature
                'public_key': The bytes corresponding the public key.
        """
        if len(self.ast) != 2:
            raise TypeError("Script is not a P2PKH signature script")

        try:
            sig_hex = self.ast[0]
            if sig_hex.startswith("0x"):
                sig_hex = sig_hex[2:]
            sig_bytes = bytes.fromhex(sig_hex)
            hash_type = sig_bytes[-1]
            sig = Signature.from_der(sig_bytes[:-1])
        except ValueError as e:
            raise TypeError("Signature does not appear to be valid")

        try:
            pub_key_hex = self.ast[1]
            if pub_key_hex.startswith("0x"):
                pub_key_hex = pub_key_hex[2:]
            pub_key_bytes = bytes.fromhex(pub_key_hex)
            pub_key = PublicKey.from_bytes(pub_key_bytes)
        except ValueError:
            raise TypeError("Public key does not appear to be valid")

        return dict(hash_type=hash_type,
                    signature=sig_bytes,
                    public_key=pub_key_bytes)

    def extract_multisig_redeem_info(self):
        """ Returns information about the multisig redeem script

        Returns:
            dict: Contains the following list of keys:
               'm' (int): Required number of signatures.
               'n' (int): Maximum number of signatures.
               'public_keys' (list): List of byte strings
                   corresponding to public keys.
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
                'signatures' (list): List of DER-encoded signatures with
                    hash_type appended at the end of the byte string.
                'redeem_script' (Script): The associated redeem script.
        """
        ast = self.ast

        # A signature script should start with OP_0
        if ast[0] != 'OP_0':
            raise TypeError("Script does not start with OP_0!")

        # Everything after OP_0 and before the last operand is a signature.
        # If it does not start with '0x', something is wrong.
        sigs = []
        for i, x in enumerate(ast[1:-1]):
            if isinstance(x, str) and x.startswith('0x'):
                sigs.append(bytes.fromhex(x[2:]))
            else:
                raise TypeError(
                    "Operand %d does not seem to be a signature!" % i)

        # The last operand should be the redeem script
        r = ast[-1]
        if isinstance(r, list):
            if not r[0].startswith('OP_PUSHDATA'):
                raise TypeError(
                    "Expecting an OP_PUSHDATA but got %s" % r[0])
            script_bytes = bytes.fromhex(r[-1][2:])  # Skip the 0x
        else:
            script_bytes = bytes.fromhex(r[2:])  # Skip the 0x
        redeem_script = Script(script_bytes)

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
            d (str or None): the hash160 (hex-encoded) or None.
        """
        if not self._ast:
            self._parse()

        # Scan for OP_HASH160
        for i, opcode in enumerate(self._ast):
            if opcode == "OP_HASH160":
                return self._ast[i+1]

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

        return rv

    def remove_op(self, op):
        """ Returns a new script without any OP_<op>'s in it.

        Returns:
            scr (Script): New script object devoid of any OP_<op>.
        """
        if op not in self.BTC_OPCODE_TABLE:
            raise ValueError("Unknown op (%s)" % (op))

        return Script(" ".join([t for t in str(self).split() if t != op]))

    def _parse(self):
        """ This is a basic Recursive Descent Parser for the Bitcoin
            script language. It will tokenize the input script to allow
            interpretation of that script. The resultant tokens are stored
            in ``self._ast``.
        """
        if self.script is None and self.raw_script is not None:
            self._disassemble(self.raw_script)

        self._ast = []
        self.tokens = self.script.split()

        self._ast = self._do_parse()

    def _do_parse(self, in_if_else=False):
        if_clause = None
        else_clause = None
        ast = []
        while self.tokens:
            opcode = self.tokens.pop(0)
            if opcode in ['OP_0', 'OP_FALSE']:
                ast.append(opcode)
            elif opcode.startswith("0x"):
                data = bytes.fromhex(opcode[2:])
                if len(data) < 0x01 or len(data) > 0x4b:
                    raise ValueError("Opcode has too much data to push onto stack: \"%s\"" % opcode)
                ast.append(opcode)
            elif opcode in ['OP_PUSHDATA1', 'OP_PUSHDATA2', 'OP_PUSHDATA4']:
                # Easy enough that we don't need to recurse here
                datalen = self.tokens.pop(0)
                data = self.tokens.pop(0)
                ast.append([opcode, datalen, data])
            elif opcode in ['OP_IF', 'OP_NOTIF']:
                # Recursively descend
                if_clause = self._do_parse(True)

                token = [opcode, if_clause]

                # Check for an else clause
                if self.tokens[0] == 'OP_ELSE':
                    self.tokens.pop(0)
                    else_clause = self._do_parse(True)
                    token.append(else_clause)

                ast.append(token)
            elif opcode in ['OP_ELSE', 'OP_ENDIF']:
                if in_if_else is None:
                    raise ParsingError("Illegal %s when not in if/else." %
                                       opcode)

                if opcode == 'OP_ELSE':
                    self.tokens = [opcode] + self.tokens

                break
            else:
                # Everything else can just be put on as a normal token
                ast.append(opcode)

        return ast

    def _disassemble(self, raw):
        """ Disassembles a raw script (in bytes) to human-readable text
            using the opcodes in BTC_OPCODE_TABLE. The disassembled string
            is stored in self.script.

        Args:
            raw (bytes): A byte stream containing the script to be
                disassembled.
        """
        script = []
        while raw:
            op, raw = raw[0], raw[1:]
            if op == 0x00:
                script.append('OP_0')
            elif op < 0x4b:
                script.append('0x%s' % (bytes_to_str(raw[0:op])))
                raw = raw[op:]
            else:
                opcode = Script.BTC_OPCODE_REV_TABLE[op]
                if opcode in ['OP_PUSHDATA1', 'OP_PUSHDATA2', 'OP_PUSHDATA4']:
                    pushlen = int(opcode[-1])
                    datalen = 0
                    if pushlen == 1:
                        datalen, raw = raw[0], raw[1:]
                    elif pushlen == 2:
                        datalen, raw = struct.unpack("<H", raw[0:2])[0], raw[2:]
                    elif pushlen == 4:
                        datalen, raw = struct.unpack("<I", raw[0:4])[0], raw[4:]

                    script.append('OP_PUSHDATA%d 0x%x 0x%s' %
                                  (pushlen,
                                   datalen,
                                   bytes_to_str(raw[:datalen])))
                    raw = raw[datalen:]
                else:
                    script.append(opcode)

        self.script = " ".join(script)

    def __str__(self):
        """ Creates a human-readable string representation of the script.

        Returns:
            s (str): String representation of the script
        """
        if self.script is None:
            # Hasn't been disassambled yet...
            self._disassemble(self.raw_script)

        return self.script

    def __bytes__(self):
        """ Serializes the object into a byte stream.
            It does *not* prepend the length of the script to the returned
            bytes. To do so, call two1.bitcoin.utils.pack_var_str() passing
            in the returned bytes.

        Returns:
            b (bytes): a serialized byte stream of this Script object.
        """
        if self.raw_script is None:
            if len(self._ast) == 0:
                self._parse()
            self.raw_script = Script._walk_ast(self._ast,
                                               Script._ser_dispatch_table,
                                               Script._serialize_var_data,
                                               b'')

        return self.raw_script
