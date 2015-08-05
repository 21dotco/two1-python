import struct

from two1.bitcoin.exceptions import ParsingError
from two1.bitcoin.utils import bytes_to_str, pack_var_str, unpack_var_str, render_int

class Script(object):
    """ Handles all Bitcoin script-related needs.
        Currently this means: parsing text scripts, assembling/disassembling and
        serialization/deserialization.

        If a raw byte stream is passed in, disassembly and parsing are deferred until
        required. If parsing is immediately required, call Script.parse() after constructing
        the object.

    Args:
        script (bytes or str): Either a text or byte string containing the script to build.
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

        bytestr += cls._walk_ast(args[0], cls._ser_dispatch_table, cls._serialize_var_data, b'')

        if len(args) == 2:
            bytestr += bytes([cls.BTC_OPCODE_TABLE['OP_ELSE']])
            bytestr += cls._walk_ast(args[1], cls._ser_dispatch_table, cls._serialize_var_data, b'')
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
            b (bytes): A byte-stream containing the script, with the length of 
                       the script in bytes prepended.

        Returns:
            (scr, b) (tuple): A tuple with the deserialized Script object and the
                              remainder of the byte stream.
        """
        raw_script, b = unpack_var_str(b)
        
        return (Script(raw_script), b)
    
    @staticmethod
    def build_p2pkh(hash160_key):
        """ Builds a Pay-to-Public-Key-Hash script.
            
        Args:
            hash160_key (bytes): the RIPEMD-160 hash of the public key in internal byte order.

        Returns:
            scr (Script): a serializable Script object containing the p2pkh script.
        """
        return Script('OP_DUP OP_HASH160 0x%s OP_EQUALVERIFY OP_CHECKSIG' % bytes_to_str(hash160_key))

    @staticmethod
    def build_p2sh(hash160_key):
        """ Builds a Pay-to-Script-Hash script.
            
        Args:
            hash160_key (bytes): the RIPEMD-160 hash of the script in internal byte order.

        Returns:
            scr (Script): a serializable Script object containing the p2sh script.
        """

        return Script('OP_HASH160 0x%s OP_EQUAL' % bytes_to_str(hash160_key))

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

        return bytes(Script('OP_PUSHDATA%d 0x%s' % (pd_index, hexstr)))

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

    def __init__(self, script):
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
        if_opcode = None
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
                    raise ParsingError("Illegal %s when not in if/else." % opcode)

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
            raw (bytes): A byte stream containing the script to be disassembled.
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

                    script.append('OP_PUSHDATA%d 0x%x 0x%s' % (pushlen, datalen, bytes_to_str(raw[:datalen])))
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
        if self.raw_script is not None:
            return self.raw_script
        if len(self._ast) == 0:
            self._parse()
        return Script._walk_ast(self._ast, Script._ser_dispatch_table, Script._serialize_var_data, b'')


if __name__ == '__main__':
    scr = 'OP_ADD OP_IF OP_DUP OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY OP_CHECKSIG OP_ELSE OP_IF OP_DUP OP_ELSE OP_2ROT OP_ENDIF OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUAL OP_ENDIF OP_PUSHDATA1 0x4e 0x010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101'

    s = Script(scr)
    assert s.raw_script is None
    assert s.script == scr
    print(s.ast)
    s_bytes = bytes(s)
    s_hex_str = bytes_to_str(s_bytes)
    print(s_hex_str)
    print(s)

    s1 = Script.from_bytes(pack_var_str(s_bytes))[0]
    assert s1.raw_script == s_bytes
    print(s1.ast)
    

    raw_scr = "483045022100d60baf72dbaed8d15c3150e3309c9f7725fbdf91b0560330f3e2a0ccb606dfba02206422b1c73ce390766f0dc4e9143d0fbb400cc207e4a9fd9130e7f79e52bf81220121034ccd52d8f72cfdd680077a1a171458a1f7574ebaa196095390ae45e68adb3688"
    s = Script(bytes.fromhex(raw_scr))
    assert s.raw_script is not None
    assert s.script is None

    print(s)
    
    s_hex_str = bytes_to_str(bytes(s))
    assert s_hex_str == raw_scr
    assert s.script is not None

    s._parse()
    assert s.script is not None
          
