"""This submodule provides a single ScriptInterpreter class to be used in
conjunciton with a Script class for deserialization and validation."""
from collections import deque
import copy
import hashlib
import struct

from two1.bitcoin.crypto import PublicKey
from two1.bitcoin.crypto import Signature
from two1.bitcoin.exceptions import ScriptInterpreterError
from two1.bitcoin.hash import Hash
from two1.bitcoin.script import Script
from two1.bitcoin import utils


class ScriptInterpreter(object):
    """ This class interprets/evaluates Bitcoin scripts.

        It is only meant to be used in conjunction with Script
        objects as it is specific to the parsing done by that class.

        The main interface is to create a ScriptInterpreter object,
        optionally passing in a transaction into the txn arg, and then
        running arbitrary number of scripts which make use of the same
        stack (and transaction).

    Args:
        txn (Transaction): If provided, should be a Transaction object
            which the script is part of.
        input_index (int): The index of the input in the transaction for
            which the script is being run.
        sub_script (Script): A Script object that replaces the input
            signature script when verifying the transaction. In the
            case of a P2PKH UTXO, this will be the UTXO scriptPubKey.
            In the case of a P2SH UTXO, this will be the redeemScript.
    """
    DISABLED_OPS = ['OP_CAT', 'OP_SUBSTR', 'OP_LEFT', 'OP_RIGHT',
                    'OP_INVERT', 'OP_AND', 'OP_OR', 'OP_XOR',
                    'OP_2MUL', 'OP_2DIV', 'OP_MUL', 'OP_DIV', 'OP_MOD',
                    'OP_LSHIFT', 'OP_RSHIFT']
    RESERVED_WORDS = ['OP_RESERVED', 'OP_VER', 'OP_VERIF', 'OP_VERNOTIF'
                      'OP_RESERVED1', 'OP_RESERVED2']
    NOP_WORDS = ['OP_NOP%d' for i in [1] + list(range(3, 11))]

    def __init__(self, txn=None, input_index=-1, sub_script=None):
        self._stack = deque()
        self._alt_stack = deque()
        self._stack_copy = None

        self._txn = txn
        self._input_index = input_index
        self._sub_script = sub_script
        self.stop = False

        self._if_else_stack = deque()

    def _walk_ast(self, ast):
        for a in ast:
            total_stack_size = len(self._stack) + len(self._alt_stack)
            if total_stack_size > 1000:
                raise ScriptInterpreterError(
                    "Too many items (%d) on the stack!" % total_stack_size)
            if self.stop:
                break

            opcode = None
            args = None
            if isinstance(a, list):
                opcode = a[0]
                args = a[1:]
            else:
                opcode = a

            if opcode in self.DISABLED_OPS + self.RESERVED_WORDS:
                self.stop = True
                break

            if opcode in Script.BTC_OPCODE_TABLE:
                op = Script.BTC_OPCODE_TABLE[opcode]
            else:
                op = None

            if opcode == "OP_0":
                self._op_0()
            elif isinstance(opcode, bytes):
                self._op_push(opcode)
            elif opcode in ['OP_PUSHDATA1', 'OP_PUSHDATA2', 'OP_PUSHDATA4']:
                pushlen = int(opcode[-1])
                if pushlen == 1:
                    datalen = args[0][0]
                elif pushlen == 2:
                    datalen = struct.unpack("<H", args[0])[0]
                elif pushlen == 4:
                    datalen = struct.unpack("<I", args[0])[0]
                data = args[1]
                if pushlen != (datalen.bit_length() + 7) // 8:
                    raise ScriptInterpreterError(
                        "datalen does not correspond with opcode")
                if len(data) != datalen:
                    raise ScriptInterpreterError(
                        "len(data) != datalen in %s" % opcode)
                self._op_pushdata(datalen, data)
            elif op and op >= Script.BTC_OPCODE_TABLE['OP_1'] and op <= Script.BTC_OPCODE_TABLE['OP_16']:
                self._op_pushnum(opcode)
            elif opcode in ['OP_IF', 'OP_NOTIF']:
                self._op_if(opcode, args)
            elif hasattr(self, "_" + opcode.lower()):
                f = getattr(self, "_" + opcode.lower())
                f()

    def run_script(self, script):
        """ Runs a script

        Args:
            script (Script): A Script object to evaluate
        """
        if not self.stop:
            self._walk_ast(script.ast)

    @property
    def valid(self):
        """ Returns whether the script is valid
        """
        return not self.stop and self._get_bool(pop=False)

    @property
    def stack(self):
        """ Getter for the stack
        """
        return self._stack

    def copy_stack(self):
        """ Copies the current stack
        """
        self._stack_copy = copy.deepcopy(self._stack)

    def restore_stack(self):
        """ Restores the stack to a previously copied stack
        """
        if self._stack_copy is not None:
            self._stack = self._stack_copy
            self._stack_copy = None
        else:
            raise ValueError("Stack must be copied before it can be restored.")

    def _check_stack_len(self, min_len, alt=False):
        """ Checks that the stack has a minimum number
            of elements.

        Args:
            min_len (int): The minimum number of elements
                that should be on the stack.
            alt (bool): If True, checks the altstack.

        Raises:
            ValueError: If the number of stack elements is fewer
                 than min_len.
        """
        s = self._alt_stack if alt else self._stack
        if len(s) < min_len:
            raise ScriptInterpreterError(
                "Stack has fewer than %d operands." % min_len)

    def _check_txn(self):
        """ Checks that a transaction object has been initialized
            in self._data.

        Raises:
            ValueError: If there is no Transaction object in self._data
        """
        from two1.bitcoin.txn import Transaction
        if not isinstance(self._txn, Transaction):
            raise ScriptInterpreterError("No transaction found!")

        if self._input_index < 0 or self._input_index >= len(self._txn.inputs):
            raise ValueError("Invalid input index.")

        if self._sub_script is None:
            raise ValueError("sub_script must not be None.")

        if not isinstance(self._sub_script, Script):
            raise TypeError("sub_script must be a Script object.")

    def _get_int(self, pop=True):
        """ Casts the top stack element to an integer.

        Args:
            pop (bool): If True, removes the top stack element.

        Returns:
            int: The top stack element casted to an integer.
        """
        x = self._stack[-1]
        if pop:
            self._stack.pop()

        if isinstance(x, bytes):
            if x:
                # Handle bitcoin's weird negative representation
                negative = x[-1] & 0x80
                _x = x[0:-1] + bytes([x[-1] & 0x7f])
                x = int.from_bytes(_x, byteorder='little')
                if negative:
                    x = -x
            else:
                # Null-length byte vector is positive 0
                x = 0

        return x

    def _get_bool(self, pop=True):
        """ Casts the top stack element to a boolean.

        Args:
            pop (bool): If True, removes the top stack element.

        Returns:
            bool: The top stack element casted to a boolean.
        """
        x = self._stack[-1]
        if pop:
            self._stack.pop()

        rv = False
        if isinstance(x, bytes):
            if len(x) > 0:
                # Try casting to an int
                i = int.from_bytes(x, 'big')
                rv = bool(i)
        elif isinstance(x, str):
            if len(x) > 0:
                i = int(x, 0)
                rv = bool(i)
        elif isinstance(x, int):
            rv = bool(x)

        return rv

    def _op_0(self):
        """ OP_0, OP_FALSE

            Empty array of bytes is pushed onto the stack.
        """
        self._stack.append(b'')

    def _op_push(self, data):
        """ Next opcode bytes are pushed onto stack

        Args:
            data (bytes): Array of bytes of at least opcode length.
        """
        if len(data) < 0x01 or len(data) > 0x4b:
            raise ScriptInterpreterError(
                "data must only be between 1 and 75 bytes long")

        self._stack.append(data)

    def _op_pushdata(self, datalen, data):
        """ Next byte(s) determines number of bytes that are pushed onto
            stack

        Args:
            datalen (int): Number of bytes to be pushed
            data (bytes): Array of bytes.
        """
        if len(data) < datalen:
            raise ScriptInterpreterError(
                "data should have at least %d bytes but has only %d." %
                (datalen, len(data)))

        self._stack.append(data)

    def _op_1negate(self):
        """ Pushes -1 onto the stack
        """
        self._stack.append(-1)

    def _op_pushnum(self, opcode):
        """ Pushes the number in opcode onto the stack
        """
        op_int = Script.BTC_OPCODE_TABLE[opcode]
        base = Script.BTC_OPCODE_TABLE['OP_1'] - 1
        self._stack.append(op_int - base)

    # Flow control ops
    def _op_nop(self):
        """ Does nothing.
        """
        pass

    def _op_if(self, opcode, data):
        """ If the top stack value is not 0 (OP_IF) or 1 (OP_NOTIF),
            the statements are executed. The top stack value is
            removed.
        """
        self._check_stack_len(1)
        do = self._get_bool()
        if opcode == 'OP_NOTIF':
            do = not do

        if do:
            self._if_else_stack.append(do)
            self._walk_ast(data[0])
        elif len(data) == 3:
            self._if_else_stack.append(do)
            self._op_else(data[1])

        if data[-1] == "OP_ENDIF":
            if self._if_else_stack:
                self._op_endif()
        else:
            raise ScriptInterpreterError("No matching OP_ENDIF!")

    def _op_else(self, data):
        """ If the preceding OP_IF or OP_NOTIF or OP_ELSE was not
            executed then these statements are and if the preceding OP_IF
            or OP_NOTIF or OP_ELSE was executed then these statements are
            not.
        """
        if len(self._if_else_stack) == 0:
            self.stop = True
            raise ScriptInterpreterError("In OP_ELSE without OP_IF/NOTIF")

        if not self._if_else_stack[-1]:
            self._walk_ast(data)

    def _op_endif(self):
        """ Ends an if/else block. All blocks must end, or the
            transaction is invalid. An OP_ENDIF without OP_IF earlier is
            also invalid.
        """
        if len(self._if_else_stack) == 0:
            self.stop = True
            raise ScriptInterpreterError("OP_ENDIF without OP_IF/NOTIF")

        self._if_else_stack.pop()

    def _op_verify(self):
        x = self._get_int()
        if not x:
            self.stop = True

    def _op_return(self):
        self.stop = True

    # Stack ops
    def _op_toaltstack(self):
        """ Puts the input onto the top of the alt stack. Removes it
            from the main stack.
        """
        self._check_stack_len(1)
        self._alt_stack.append(self._stack.pop())

    def _op_fromaltstack(self):
        """ Puts the input onto the top of the main stack. Removes it
            from the alt stack.
        """
        self._check_stack_len(1, True)
        self._stack.append(self._alt_stack.pop())

    def _op_ifdup(self):
        """ If the top stack value is not 0, duplicate it.
        """
        self._check_stack_len(1)
        x = self._get_int(pop=False)
        if x:
            self._stack.append(x)

    def _op_depth(self):
        """ Puts the number of stack items onto the stack.
        """
        self._stack.append(len(self._stack))

    def _op_drop(self):
        """ Removes the top stack item.
        """
        self._check_stack_len(1)
        self._stack.pop()

    def _op_dup(self):
        """ Duplicates the top stack item.
        """
        self._check_stack_len(1)
        self._stack.append(self._stack[-1])

    def _op_nip(self):
        """ Removes the second-to-top stack item
        """
        self._check_stack_len(2)
        x2 = self._stack.pop()
        self._stack.pop()
        self._stack.append(x2)

    def _op_over(self):
        """ Copies the second-to-top stack item to the top
        """
        self._check_stack_len(2)
        self._stack.append(self._stack[-2])

    def _op_pick(self, roll=False):
        """ Copies the nth item in the stack to the top
        """
        self._check_stack_len(2)
        n = self._get_int()
        if n <= 0 or n >= len(self._stack):
            self.stop = True
            raise ScriptInterpreterError("n (%d) is invalid." % n)
        x = self._stack[-n]
        if roll:
            del self._stack[-n]
        self._stack.append(x)

    def _op_roll(self):
        """ Moves the nth item in the stack to the top
        """
        self._op_pick(roll=True)

    def _op_rot(self):
        """ The top 3 items on the stack are rotated to the left
        """
        self._check_stack_len(3)
        x3 = self._stack.pop()
        x2 = self._stack.pop()
        x1 = self._stack.pop()
        self._stack.append(x2)
        self._stack.append(x3)
        self._stack.append(x1)

    def _op_swap(self):
        """ Top 2 items on the stack are swapped
        """
        self._check_stack_len(2)
        x2 = self._stack.pop()
        x1 = self._stack.pop()
        self._stack.append(x2)
        self._stack.append(x1)

    def _op_tuck(self):
        """ The item at the top of the stack is copied and inserted
            before the second-to-top item.
        """
        self._check_stack_len(2)
        top = self._stack[-1]
        self._stack.rotate(2)
        self._stack.append(top)
        self._stack.rotate(-2)

    def _op_2drop(self):
        """ Removes the top two stack items.
        """
        self._check_stack_len(2)
        self._stack.pop()
        self._stack.pop()

    def _op_2dup(self):
        """ Duplicates the top two stack items.
        """
        self._check_stack_len(2)
        x2 = self._stack[-1]
        x1 = self._stack[-2]
        self._stack.append(x1)
        self._stack.append(x2)

    def _op_3dup(self):
        """ Duplicates the top three stack items.
        """
        self._check_stack_len(2)
        x3 = self._stack[-1]
        x2 = self._stack[-2]
        x1 = self._stack[-3]
        self._stack.append(x1)
        self._stack.append(x2)
        self._stack.append(x3)

    def _op_2over(self):
        """ Copies the pair of items two spaces back in the stack to
            the front.
        """
        self._check_stack_len(4)
        x1 = self._stack[-4]
        x2 = self._stack[-3]
        self._stack.append(x1)
        self._stack.append(x2)

    def _op_2rot(self):
        """ The fifth and sixth items back are moved to the top of the
            stack.
        """
        self._check_stack_len(6)
        self._stack.rotate(4)
        x2 = self._stack.pop()
        x1 = self._stack.pop()
        self._stack.rotate(-4)
        self._stack.append(x1)
        self._stack.append(x2)

    def _op_2swap(self):
        """ Swaps the top two pairs of items.
        """
        self._check_stack_len(4)
        self._stack.rotate(2)
        x2 = self._stack.pop()
        x1 = self._stack.pop()
        self._stack.rotate(-2)
        self._stack.append(x1)
        self._stack.append(x2)

    # Splice ops
    def _op_size(self):
        """ Pushes the string length of the top element of the stack
            (without popping it).
        """
        self._check_stack_len(1)
        self._stack.append(len(self._stack[-1]))

    # Bitwise logic ops
    def _op_equal(self):
        self._check_stack_len(2)

        x1 = self._stack.pop()
        x2 = self._stack.pop()

        self._stack.append(x1 == x2)

    def _op_equalverify(self):
        self._op_equal()
        self._op_verify()

    # Arithmetic ops
    def _op_1add(self):
        """ 1 is added to the input.
        """
        self._check_stack_len(1)
        i = self._get_int()
        self._stack.append(i + 1)

    def _op_1sub(self):
        """ 1 is subtracted from the input.
        """
        self._check_stack_len(1)
        i = self._get_int()
        self._stack.append(i - 1)

    def _op_negate(self):
        """ The sign of the input is flipped
        """
        self._check_stack_len(1)
        i = self._get_int()
        self._stack.append(-i)

    def _op_abs(self):
        """ The input is made positive
        """
        self._check_stack_len(1)
        i = self._get_int()
        self._stack.append(abs(i))

    def _op_not(self):
        """ If the input is 0 or 1, it is flipped. Otherwise it is
            made 0.
        """
        self._check_stack_len(1)
        i = self._get_int()
        x = 0
        if i == 0:
            x = 1

        self._stack.append(x)

    def _op_0notequal(self):
        """ Returns 0 if the input is 0. 1 otherwise.
        """
        self._check_stack_len(1)
        i = self._get_int()
        if i == 0:
            x = 0
        else:
            x = 1

        self._stack.append(x)

    def _do_binary_op(self, op_func):
        self._check_stack_len(2)
        a = self._get_int()
        b = self._get_int()
        self._stack.append(op_func(a, b))

    def _op_add(self):
        """ Adds the top 2 stack items
        """
        self._do_binary_op(lambda a, b: a + b)

    def _op_sub(self):
        """ Subtracts the top stack item from the one
            2 in.
        """
        self._do_binary_op(lambda a, b: a - b)

    def _op_booland(self):
        """ If both a and b are not 0, the output is 1. Otherwise 0.
        """
        self._do_binary_op(lambda a, b: int(bool(a and b)))

    def _op_boolor(self):
        """ If a or b is not 0, the output is 1. Otherwise 0.
        """
        self._do_binary_op(lambda a, b: int(bool(a or b)))

    def _op_numequal(self):
        """ Returns 1 if the numbers are equal, 0 otherwise.
        """
        self._do_binary_op(lambda a, b: int(a == b))

    def _op_numequalverify(self):
        """ Same as OP_NUMEQUAL but runs OP_VERIFY afterwards.
        """
        self._op_numequal()
        self._op_verify()

    def _op_numnotequal(self):
        """ Returns 1 if the numbers are not equal, 0 otherwise.
        """
        self._do_binary_op(lambda a, b: int(a != b))

    def _op_lessthan(self):
        """ Returns 1 if a is less than b, 0 otherwise.
        """
        self._do_binary_op(lambda a, b: int(a < b))

    def _op_greaterthan(self):
        """ Returns 1 if a is greater than b, 0 otherwise.
        """
        self._do_binary_op(lambda a, b: int(a > b))

    def _op_lessthanequal(self):
        """ Returns 1 if a is less than or equal to b, 0 otherwise.
        """
        self._do_binary_op(lambda a, b: int(a <= b))

    def _op_greaterthanequal(self):
        """ Returns 1 if a is greater than or equal to b, 0 otherwise.
        """
        self._do_binary_op(lambda a, b: int(a >= b))

    def _op_min(self):
        """ Returns the smaller of a and b
        """
        self._do_binary_op(min)

    def _op_max(self):
        """ Returns the larger of a and b
        """
        self._do_binary_op(max)

    def _op_within(self):
        """ Returns 1 if x is within the specified range
            (left-inclusive), 0 otherwise.
        """
        self._check_stack_len(3)
        mx = self._get_int()
        mn = self._get_int()
        x = self._get_int()
        self._stack.append(int(mn <= x and x < mx))

    # Crypto ops
    def _op_ripemd160(self):
        """ The input is hashed using RIPEMD-160.
        """
        self._check_stack_len(1)

        x = self._stack.pop()
        r = hashlib.new('ripemd160')
        r.update(x)
        self._stack.append(r.digest())

    def _op_sha1(self):
        """ The input is hashed using SHA-1.
        """
        self._check_stack_len(1)

        x = self._stack.pop()
        self._stack.append(hashlib.sha1(x).digest())

    def _op_sha256(self):
        """ The input is hashed using SHA-256.
        """
        self._check_stack_len(1)

        x = self._stack.pop()
        self._stack.append(hashlib.sha256(x).digest())

    def _op_hash160(self):
        """ The input is hashed twice: first with SHA-256 and then
            with RIPEMD-160.
        """
        self._check_stack_len(1)

        x = self._stack.pop()
        self._stack.append(utils.hash160(x))

    def _op_hash256(self):
        """ The input is hashed two times with SHA-256.
        """
        self._check_stack_len(1)

        x = self._stack.pop()
        self._stack.append(bytes(Hash.dhash(x)))

    def _op_codeseparator(self):
        """ All of the signature checking words will only match
            signatures to the data after the most recently-executed
            OP_CODESEPARATOR.
        """
        pass

    def _op_checksig(self):
        """ The entire transaction's outputs, inputs, and script (from
            the most recently-executed OP_CODESEPARATOR to the end) are
            hashed. The signature used by OP_CHECKSIG must be a valid
            signature for this hash and public key. If it is, 1 is
            returned, 0 otherwise.
        """
        self._check_stack_len(2)
        self._check_txn()

        pub_key_bytes = self._stack.pop()
        s = self._stack.pop()
        sig_der, hash_type = s[:-1], s[-1]

        pub_key = PublicKey.from_bytes(pub_key_bytes)
        sig = Signature.from_der(sig_der)

        txn_copy = self._txn._copy_for_sig(input_index=self._input_index,
                                           hash_type=hash_type,
                                           sub_script=self._sub_script)
        msg = bytes(txn_copy) + utils.pack_u32(hash_type)
        tx_digest = hashlib.sha256(msg).digest()

        verified = pub_key.verify(tx_digest, sig)

        self._stack.append(verified)

    def _op_checksigverify(self):
        """ Same as OP_CHECKSIG, but OP_VERIFY is executed afterward.
        """
        self._op_checksig()
        self._op_verify()

    def _op_checkmultisig(self, partial=False):
        """ Compares the first signature against each public key until
            it finds an ECDSA match. Starting with the subsequent public
            key, it compares the second signature against each remaining
            public key until it finds an ECDSA match. The process is
            repeated until all signatures have been checked or not enough
            public keys remain to produce a successful result. All
            signatures need to match a public key. Because public keys are
            not checked again if they fail any signature comparison,
            signatures must be placed in the scriptSig using the same
            order as their corresponding public keys were placed in the
            scriptPubKey or redeemScript. If all signatures are valid, 1
            is returned, 0 otherwise. Due to a bug, one extra unused value
            is removed from the stack.
        """
        self._check_stack_len(1)
        self._check_txn()

        num_keys = self._stack.pop()
        self._check_stack_len(num_keys)

        keys_bytes = []
        for i in range(num_keys):
            keys_bytes.insert(0, self._stack.pop())
        public_keys = [PublicKey.from_bytes(p) for p in keys_bytes]

        min_num_sigs = self._stack.pop()

        # Although "m" is the *minimum* number of required signatures, bitcoin
        # core only consumes "m" signatures and then expects an OP_0. This
        # means that if m < min_num_sigs <= n, bitcoin core will return a
        # script failure. See:
        # https://github.com/bitcoin/bitcoin/blob/0.10/src/script/interpreter.cpp#L840
        # We will do the same.
        hash_types = set()
        sigs = []
        for i in range(min_num_sigs):
            s = self._stack.pop()
            try:
                sig = Signature.from_der(s[:-1])
                hash_types.add(s[-1])
                sigs.insert(0, sig)
            except ValueError:
                if partial:
                    # Put it back on stack
                    self._stack.append(s)
                else:
                    # If not a partial evaluation there are not enough
                    # sigs
                    rv = False
                break

        if len(hash_types) != 1:
            raise ScriptInterpreterError("Not all signatures have the same hash type!")

        hash_type = hash_types.pop()
        txn_copy = self._txn._copy_for_sig(input_index=self._input_index,
                                           hash_type=hash_type,
                                           sub_script=self._sub_script)

        msg = bytes(txn_copy) + utils.pack_u32(hash_type)
        txn_digest = hashlib.sha256(msg).digest()

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
        if len(self._stack) == 1:
            rv &= self._stack.pop() == b''
            rv &= len(self._stack) == 0
        else:
            rv = False

        self._stack.append(rv)
        if partial:
            self.match_count = match_count

    def _op_checkpartialmultisig(self):
        """ This is an internal op used for checking partially
            signed multi-sig transactions.
        """
        self._op_checkmultisig(partial=True)

    def _op_checkmultisigverify(self):
        """ Same as OP_CHECKMULTISIG, but OP_VERIFY is executed
            afterward.
        """
        self._op_checkmultisig()
        self._op_verify()

    def _op_checklocktimeverify(self):
        """ Marks transaction as invalid if the top stack item is
            greater than the transaction's nLockTime field, otherwise
            script evaluation continues as though an OP_NOP was
            executed. Transaction is also invalid if 1. the top stack item
            is negative; or 2. the top stack item is greater than or equal
            to 500000000 while the transaction's nLockTime field is less
            than 500000000, or vice versa; or 3. the input's nSequence
            field is equal to 0xffffffff.
        """
        lt_thresh = 500000000
        self._check_txn()
        self._check_stack_len(1)

        lock_time = self._get_int(pop=False)
        if lock_time < 0:
            self.stop = True
            return

        # Do the actual checks here
        if not (self._txn.lock_time < lt_thresh and lock_time < lt_thresh or
                self._txn.lock_time >= lt_thresh and lock_time >= lt_thresh):
            self.stop = True
            return

        # Check against the txn lock time
        if lock_time > self._txn.lock_time:
            self.stop = True
            return

        # Finally check that the input hasn't been finalized
        inp = self._txn.inputs[self._input_index]
        if inp.sequence_num == 0xffffffff:
            self.stop = True
