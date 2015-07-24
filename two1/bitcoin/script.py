from two1.bitcoin.exceptions import ParsingError
from two1.bitcoin.utils import bytes_to_str, pack_var_str, unpack_var_str, address_to_key

class Script(object):
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

    @staticmethod
    def from_bytes(b):
        ''' Assumes the first part contains the length of the
            script in bytes
        '''
        raw_script, b = unpack_var_str(b)
        
        return (Script(raw_script, True), b)
    
    @staticmethod
    def build_p2pkh(hash160_address):
        return Script('OP_DUP OP_HASH160 0x%s OP_EQUALVERIFY OP_CHECKSIG' % bytes_to_str(hash160_address))

    @staticmethod
    def build_p2sh(hash160_address):
        return Script('OP_HASH160 0x%s OP_EQUAL' % bytes_to_str(hash160_address))

    # Following two functions might not be necessary anymore
    @staticmethod
    def make_lock_script(version, key):
        if version in (5, 196):  # P2SH mainnet, testnet.
            return Script.build_p2sh(key)
        elif version in (0, 111):  # P2PKH mainnet, testnet.
            return Script.build_p2pkh(key)
        else:
            raise ValueError("Unrecognized key version: %d" % version)

    @staticmethod
    def make_oscript(addr):
        version, key = address_to_key(addr)
        return Script.make_lock_script(version, key)

    def __init__(self, script, raw=False):
        ''' script: Either a text or byte string containing the script to build.
                    If script is a byte string, raw must be set to True.
        '''

        self.ser_dispatch_table = {}
        for k, v in self.BTC_OPCODE_TABLE.items():
            if k in ['OP_PUSHDATA1', 'OP_PUSHDATA2', 'OP_PUSHDATA4']:
                self.ser_dispatch_table[k] = self._serialize_pushdata
            elif k in ['OP_IF', 'OP_NOTIF']:
                self.ser_dispatch_table[k] = self._serialize_if_else
            else:
                self.ser_dispatch_table[k] = self._serialize_default_opcode
        
        self.script = None
        self.raw_script = None
        self.ast = []

        if raw:
            self.raw_script = script
        else:
            self.script = script
            self.parse()

    def parse(self):
        ''' This is a basic Recursive Descent Parser for the Bitcoin
            script language. It will tokenize the input script to allow
            interpretation of that script.
        '''
        print(self.script is None, self.raw_script is not None)
        if self.script is None and self.raw_script is not None:
            print("lazily disassembling")
            self.disassemble(self.raw_script)
        
        self.ast = []
        self.tokens = self.script.split()

        self.ast = self.__parse__()

    def __parse__(self, in_if_else=False):
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
                if_clause = self.__parse__(True)

                token = [opcode, if_clause]
                
                # Check for an else clause
                if self.tokens[0] == 'OP_ELSE':
                    self.tokens.pop(0)
                    else_clause = self.__parse__(True)
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
    
    def disassemble(self, raw):
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

    def _walk_ast(self, ast, dispatch_table, default_handler=None, data=None):
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

    def _serialize_pushdata(self, opcode, args, bytestr):
        pushlen = int(opcode[-1])

        if len(args) < 2:
            raise ValueError("Not enough arguments for %s" % opcode)
        
        datalen = int(args[0], 0)
        pushdata = args[1]
                
        bytestr += bytes([self.BTC_OPCODE_TABLE[opcode]])
                
        if pushlen == 1:
            bytestr += bytes([datalen])
        elif pushlen == 2:
            bytestr += struct.pack("<H", datalen)
        elif pushlen == 4:
            bytestr += struct.pack("<I", datalen)
            
        bytestr += bytes.fromhex(pushdata[2:])
        return bytestr

    def _serialize_var_data(self, opcode, args, bytestr):
        data = bytes.fromhex(opcode[2:])
        if len(data) < 0x01 or len(data) > 0x4b:
            raise ValueError("Opcode has too much data to push onto stack: \"%s\"" % opcode)
        bytestr += bytes([len(data)])
        bytestr += data

        return bytestr

    def _serialize_if_else(self, opcode, args, bytestr):
        bytestr += bytes([self.BTC_OPCODE_TABLE[opcode]])

        if len(args) == 0:
            raise ValueError("Not enough clauses for %s!" % opcode)

        bytestr += self._walk_ast(args[0], self.ser_dispatch_table, self._serialize_var_data, b'')

        if len(args) == 2:
            bytestr += bytes([self.BTC_OPCODE_TABLE['OP_ELSE']])
            bytestr += self._walk_ast(args[1], self.ser_dispatch_table, self._serialize_var_data, b'')
            bytestr += bytes([self.BTC_OPCODE_TABLE['OP_ENDIF']])

        return bytestr

    def _serialize_default_opcode(self, opcode, args, bytestr):
        bytestr += bytes([self.BTC_OPCODE_TABLE[opcode]])

        return bytestr

    def __bytes__(self):
        if self.raw_script is not None:
            return self.raw_script
        if len(self.ast) == 0:
            self.parse()
        return self._walk_ast(self.ast, self.ser_dispatch_table, self._serialize_var_data, b'')


if __name__ == '__main__':
    scr = 'OP_ADD OP_IF OP_DUP OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY OP_CHECKSIG OP_ELSE OP_IF OP_DUP OP_ELSE OP_2ROT OP_ENDIF OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUAL OP_ENDIF OP_PUSHDATA1 0x4e 0x010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101'

    s = Script(scr)
    assert s.raw_script is None
    assert s.script == scr
    print(s.ast)
    s_bytes = bytes(s)
    s_hex_str = bytes_to_str(s_bytes)
    print(s_hex_str)

    s1 = Script.from_bytes(pack_var_str(s_bytes))[0]
    assert s1.raw_script == s_bytes
    print(s1.ast)
    

    raw_scr = "483045022100d60baf72dbaed8d15c3150e3309c9f7725fbdf91b0560330f3e2a0ccb606dfba02206422b1c73ce390766f0dc4e9143d0fbb400cc207e4a9fd9130e7f79e52bf81220121034ccd52d8f72cfdd680077a1a171458a1f7574ebaa196095390ae45e68adb3688"
    s = Script(bytes.fromhex(raw_scr), True)
    assert s.raw_script is not None
    assert s.script is None

    s_hex_str = bytes_to_str(bytes(s))
    assert s_hex_str == raw_scr
    assert s.script is None

    s.parse()
    assert s.script is not None
          
