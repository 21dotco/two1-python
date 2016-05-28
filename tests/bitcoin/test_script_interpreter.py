import pytest

from two1.bitcoin.hash import Hash
from two1.bitcoin.exceptions import ScriptInterpreterError
from two1.bitcoin.script import Script
from two1.bitcoin.script_interpreter import ScriptInterpreter
from two1.bitcoin.txn import Transaction
from two1.bitcoin.txn import TransactionInput
from two1.bitcoin.txn import TransactionOutput
from two1.bitcoin import utils


def test_op_0():
    s = Script("OP_0")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert si.stack[0] == b''


def test_op_push():
    s = Script("0x02 0x03")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 2
    assert si.stack[0] == b'\x02'
    assert si.stack[1] == b'\x03'


def test_op_pushdata():
    s = Script("0x" + "12" * 0x4e)

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert si.stack[0] == bytes([0x12] * 0x4e)

    s = Script("0x" + "12" * 0x4eff)
    si.run_script(s)

    assert len(si.stack) == 2
    assert si.stack[1] == bytes([0x12] * 0x4eff)


def test_op_1negate():
    s = Script("OP_1NEGATE")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert si.stack[0] == -1


def test_op_pushnum():
    for i in range(1, 17):
        s = Script("OP_%d" % i)

        si = ScriptInterpreter()
        si.run_script(s)

        assert len(si.stack) == 1
        assert si.stack[0] == i


def test_op_if():
    s = Script("OP_1 OP_IF OP_2 OP_3 OP_ENDIF OP_4")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 3
    assert list(si.stack) == [2, 3, 4]
    assert len(si._if_else_stack) == 0

    s = Script("OP_0 OP_IF OP_2 OP_3 OP_ENDIF OP_4")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [4]
    assert len(si._if_else_stack) == 0

    s = Script("OP_1 OP_IF OP_2 OP_3 OP_IF OP_15 OP_ADD OP_ENDIF OP_ENDIF OP_4")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 2
    assert list(si.stack) == [17, 4]
    assert len(si._if_else_stack) == 0


def test_op_notif():
    s = Script("OP_1 OP_NOTIF OP_2 OP_3 OP_ENDIF OP_4")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [4]

    s = Script("OP_0 OP_NOTIF OP_2 OP_3 OP_ENDIF OP_4")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 3
    assert list(si.stack) == [2, 3, 4]


def test_op_else():
    s = Script("OP_1 OP_IF OP_2 OP_3 OP_ELSE OP_15 OP_ENDIF OP_4")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 3
    assert list(si.stack) == [2, 3, 4]
    assert len(si._if_else_stack) == 0

    s = Script("OP_0 OP_IF OP_2 OP_3 OP_ELSE OP_15 OP_ENDIF OP_4")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 2
    assert list(si.stack) == [15, 4]
    assert len(si._if_else_stack) == 0

    s = Script("OP_0 OP_IF OP_2 OP_3 OP_ELSE OP_1 OP_2 OP_SUB OP_IF OP_3 OP_ENDIF OP_ENDIF OP_4")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 2
    assert list(si.stack) == [3, 4]
    assert len(si._if_else_stack) == 0


def test_op_verify():
    s = Script("0x01 OP_VERIFY")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 0
    assert not si.stop

    s = Script("0x00 OP_VERIFY")
    si.run_script(s)

    assert len(si.stack) == 0
    assert si.stop


def test_op_return():
    s = Script("OP_RETURN 0x010203")

    si = ScriptInterpreter()
    si.run_script(s)

    assert si.stop
    assert len(si.stack) == 0


def test_op_toaltstack():
    s = Script("OP_1 OP_2 OP_TOALTSTACK")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si._alt_stack) == 1
    assert si._alt_stack[-1] == 2
    assert len(si.stack) == 1
    assert si.stack[-1] == 1


def test_op_fromaltstack():
    s = Script("OP_1 OP_2 OP_TOALTSTACK OP_FROMALTSTACK")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 2
    assert si.stack[-1] == 2
    assert si.stack[-2] == 1
    assert len(si._alt_stack) == 0


def test_op_ifdup():
    s = Script("OP_1 OP_IFDUP")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 2
    assert si.stack[-1] == 1
    assert si.stack[-2] == 1

    s = Script("OP_0 OP_IFDUP")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert si.stack[-1] == b''


def test_op_depth():
    s = Script("OP_1 OP_IFDUP OP_DEPTH")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 3
    assert list(si.stack) == [1, 1, 2]


def test_op_drop():
    s = Script("OP_1 OP_IFDUP OP_DROP")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]


def test_op_dup():
    s = Script("0x01 OP_DUP")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 2
    assert si.stack[0] == b'\x01'
    assert si.stack[1] == b'\x01'


def test_op_nip():
    s = Script("OP_1 OP_2 OP_3 OP_NIP")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 2
    assert list(si.stack) == [1, 3]


def test_op_over():
    s = Script("OP_1 OP_2 OP_3 OP_4 OP_5 OP_3 OP_OVER")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 7
    assert list(si.stack) == [1, 2, 3, 4, 5, 3, 5]


def test_op_pick():
    s = Script("OP_1 OP_2 OP_3 OP_4 OP_5 OP_4 OP_PICK")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 6
    assert list(si.stack) == [1, 2, 3, 4, 5, 2]


def test_op_roll():
    s = Script("OP_1 OP_2 OP_3 OP_4 OP_5 OP_4 OP_ROLL")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 5
    assert list(si.stack) == [1, 3, 4, 5, 2]


def test_op_rot():
    s = Script("OP_1 OP_2 OP_3 OP_4 OP_5 OP_ROT")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 5
    assert list(si.stack) == [1, 2, 4, 5, 3]


def test_op_swap():
    s = Script("OP_1 OP_2 OP_3 OP_4 OP_5 OP_SWAP")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 5
    assert list(si.stack) == [1, 2, 3, 5, 4]


def test_op_tuck():
    s = Script("OP_1 OP_2 OP_3 OP_4 OP_5 OP_TUCK")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 6
    assert list(si.stack) == [1, 2, 3, 5, 4, 5]


def test_op_2drop():
    s = Script("OP_1 OP_2 OP_3 OP_4 OP_5 OP_2DROP")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 3
    assert list(si.stack) == [1, 2, 3]


def test_op_2dup():
    s = Script("OP_1 OP_2 OP_3 OP_4 OP_5 OP_2DUP")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 7
    assert list(si.stack) == [1, 2, 3, 4, 5, 4, 5]


def test_op_3dup():
    s = Script("OP_1 OP_2 OP_3 OP_4 OP_5 OP_3DUP")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 8
    assert list(si.stack) == [1, 2, 3, 4, 5, 3, 4, 5]


def test_op_2over():
    s = Script("OP_1 OP_2 OP_3 OP_4 OP_5 OP_2OVER")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 7
    assert list(si.stack) == [1, 2, 3, 4, 5, 2, 3]


def test_op_2rot():
    s = Script("OP_1 OP_2 OP_3 OP_4 OP_5 OP_6 OP_2ROT")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 6
    assert list(si.stack) == [3, 4, 5, 6, 1, 2]


def test_op_2swap():
    s = Script("OP_1 OP_2 OP_3 OP_4 OP_5 OP_6 OP_2SWAP")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 6
    assert list(si.stack) == [1, 2, 5, 6, 3, 4]


def test_op_size():
    s = Script("OP_1 OP_2 OP_3 OP_4 OP_5 0x010203 OP_SIZE")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 7
    assert list(si.stack) == [1, 2, 3, 4, 5, b'\x01\x02\x03', 3]


def test_op_equal():
    s = Script("0x01 0x01 OP_EQUAL")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert si.stack[0] is True

    s = Script("0x01 0x02 OP_EQUAL")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert si.stack[0] is False


def test_op_1add():
    s = Script("OP_1 OP_1ADD")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [2]


def test_op_1sub():
    s = Script("OP_3 OP_1SUB")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [2]


def test_op_negate():
    s = Script("OP_3 OP_NEGATE")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [-3]

    si.run_script(Script("OP_NEGATE"))

    assert list(si.stack) == [3]


def test_op_abs():
    s = Script("OP_3 OP_NEGATE OP_ABS")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [3]


def test_op_not():
    s = Script("OP_1 OP_NOT")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [0]

    si.run_script(Script("OP_2 OP_NOT"))
    assert list(si.stack) == [0, 0]

    si.run_script(Script("OP_NOT"))
    assert list(si.stack) == [0, 1]


def test_op_0notequal():
    s = Script("OP_1 OP_0NOTEQUAL")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]

    si.run_script(Script("OP_NOT"))
    assert list(si.stack) == [0]

    si.run_script(Script("OP_0NOTEQUAL"))
    assert list(si.stack) == [0]


def test_op_add():
    s = Script("OP_1 OP_2 OP_ADD")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [3]


def test_op_sub():
    s = Script("OP_1 OP_2 OP_SUB")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]

    s = Script("OP_2 OP_1 OP_SUB")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [-1]


def test_op_booland():
    s = Script("OP_1 OP_2 OP_BOOLAND")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]

    s = Script("OP_1 OP_1 OP_NOT OP_BOOLAND")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [0]


def test_op_boolor():
    s = Script("OP_1 OP_2 OP_BOOLOR")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]

    s = Script("OP_1 OP_1 OP_NOT OP_BOOLOR")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]

    s = Script("OP_1 OP_NOT OP_1 OP_NOT OP_BOOLOR")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [0]


def test_op_numequal():
    s = Script("OP_1 OP_2 OP_NUMEQUAL")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [0]

    s = Script("OP_16 OP_16 OP_NUMEQUAL")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]


def test_op_numequalverify():
    s = Script("OP_1 OP_2 OP_NUMEQUALVERIFY OP_3")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 0
    assert list(si.stack) == []

    s = Script("OP_16 OP_16 OP_NUMEQUALVERIFY OP_3")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [3]


def test_op_numnotequal():
    s = Script("OP_1 OP_2 OP_NUMNOTEQUAL")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]

    s = Script("OP_16 OP_16 OP_NUMNOTEQUAL")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [0]


def test_op_lessthan():
    s = Script("OP_1 OP_2 OP_LESSTHAN")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [0]

    s = Script("OP_2 OP_1 OP_LESSTHAN")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]


def test_op_greaterthan():
    s = Script("OP_1 OP_2 OP_GREATERTHAN")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]

    s = Script("OP_2 OP_2 OP_GREATERTHAN")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [0]


def test_op_lessthanequal():
    s = Script("OP_1 OP_2 OP_LESSTHANEQUAL")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [0]

    s = Script("OP_2 OP_2 OP_LESSTHANEQUAL")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]


def test_op_greaterthanequal():
    s = Script("OP_1 OP_2 OP_GREATERTHANEQUAL")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]

    s = Script("OP_2 OP_1 OP_GREATERTHANEQUAL")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [0]


def test_op_min():
    s = Script("OP_1 OP_2 OP_MIN")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]

    s = Script("OP_2 OP_2 OP_MIN")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [2]


def test_op_max():
    s = Script("OP_1 OP_2 OP_MAX")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [2]

    s = Script("OP_2 OP_2 OP_MAX")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [2]


def test_op_within():
    s = Script("OP_4 OP_1 OP_15 OP_WITHIN")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]

    s = Script("OP_4 OP_5 OP_15 OP_WITHIN")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [0]

    s = Script("OP_4 OP_4 OP_15 OP_WITHIN")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [1]

    s = Script("OP_15 OP_4 OP_15 OP_WITHIN")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert list(si.stack) == [0]


def test_op_ripemd160():
    s = Script("0x01 OP_RIPEMD160")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert si.stack[0] == b'\xf2\x91\xbaP\x15\xdf4\x8c\x80\x85?\xa5\xbb\x0fyF\xf5\xc9\xe1\xb3'


def test_op_sha1():
    s = Script("0x01 OP_SHA1")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert si.stack[0] == b'\xbf\x8bE0\xd8\xd2F\xddt\xacS\xa14q\xbb\xa1yA\xdf\xf7'


def test_op_sha256():
    s = Script("0x01 OP_SHA256")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert si.stack[0] == b'K\xf5\x12/4ET\xc5;\xde.\xbb\x8c\xd2\xb7\xe3\xd1`\n\xd61\xc3\x85\xa5\xd7\xcc\xe2<w\x85E\x9a'


def test_op_hash160():
    s = Script("0x01 OP_HASH160")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert si.stack[0] == b'\xc5\x1bf\xbc\xed^D\x91\x00\x1b\xd7\x02f\x97p\xdc\xcfD\t\x82'


def test_op_hash256():
    s = Script("0x01 OP_HASH256")

    si = ScriptInterpreter()
    si.run_script(s)

    assert len(si.stack) == 1
    assert si.stack[0] == b'\x9c\x12\xcf\xdc\x04\xc7E\x84\xd7\x87\xac=#w!2\xc1\x85$\xbcz\xb2\x8d\xecB\x19\xb8\xfc[B_p'


def test_op_checksig():
    # This is from the same example as in test_signing.py
    txn = Transaction.from_hex("0100000001205607fb482a03600b736fb0c257dfd4faa49e45db3990e2c4994796031eae6e000000001976a914e9f061ff2c9885c7b137de35e416cbd5d3e1087c88acffffffff0128230000000000001976a914f1fd1dc65af03c30fe743ac63cef3a120ffab57d88ac00000000")  # nopep8

    pub_key_hex = "0x04e674caf81eb3bb4a97f2acf81b54dc930d9db6a6805fd46ca74ac3ab212c0bbf62164a11e7edaf31fbf24a878087d925303079f2556664f3b32d125f2138cbef"  # nopep8
    sig_hex = "0x3045022100ed84be709227397fb1bc13b749f235e1f98f07ef8216f15da79e926b99d2bdeb02206ff39819d91bc81fecd74e59a721a38b00725389abb9cbecb42ad1c939fd826201"  # nopep8
    s = Script("%s %s OP_CHECKSIG" % (sig_hex, pub_key_hex))
    prev_script_pub_key = Script.build_p2pkh(utils.address_to_key_hash(
        "1NKxQnbtKDdL6BY1UaKdrzCxQHfn3TQnqZ")[1])

    si = ScriptInterpreter(txn=txn,
                           input_index=0,
                           sub_script=prev_script_pub_key)
    si.run_script(s)

    assert len(si.stack) == 1
    assert si.stack[0] is True

    s = Script("%s %s OP_CHECKSIGVERIFY" % (sig_hex, pub_key_hex))

    si = ScriptInterpreter(txn=txn,
                           input_index=0,
                           sub_script=prev_script_pub_key)
    si.run_script(s)

    assert len(si.stack) == 0
    assert not si.stop

    # Try it once more with an incorrect sig
    pub_key_hex = "0x04e674caf81eb3bb4a97f2acf81b54dc930d9db6a6805fd46ca74ac3ab212c0bbf62164a11e7edaf31fbf24a878087d925303079f2556664f3b32d125f2138cbef"  # nopep8
    sig_hex = "0x3045022100ed84be709227397fc1bc13b749f235e1f98f07ef8216f15da79e926b99d2bdeb02206ff39819d91bc81fecd74e59a721a38b00725389abb9cbecb42ad1c939fd826201"  # nopep8
    s = Script("%s %s OP_CHECKSIG" % (sig_hex, pub_key_hex))

    si = ScriptInterpreter(txn=txn,
                           input_index=0,
                           sub_script=prev_script_pub_key)
    si.run_script(s)

    assert len(si.stack) == 1
    assert si.stack[0] is False

    s = Script("%s %s OP_CHECKSIGVERIFY" % (sig_hex, pub_key_hex))

    si = ScriptInterpreter(txn=txn,
                           input_index=0,
                           sub_script=prev_script_pub_key)
    si.run_script(s)

    assert len(si.stack) == 0
    assert si.stop


def test_op_checkmultisig():
    txn = Transaction.from_hex("01000000010506344de69d47e432eb0174500d6e188a9e63c1e84a9e8796ec98c99b7559f701000000fdfd00004730440220695a28c42daa23c13e192e36a20d03a2a79994e0fe1c3c6b612d0ae23743064602200ca19003e7c1ce0cecb0bbfba9a825fc3b83cf54e4c3261cd15f080d24a8a5b901483045022100aa9096ce71995c24545694f20ab0482099a98c99b799c706c333c521e51db66002206578f023fa46f4a863a6fa7f18b95eebd1a91fcdf6ce714e8795d902bd6b682b014c69522102b66fcb1064d827094685264aaa90d0126861688932eafbd1d1a4ba149de3308b21025cab5e31095551582630f168280a38eb3a62b0b3e230b20f8807fc5463ccca3c21021098babedb3408e9ac2984adcf2a8e4c48e56a785065893f76d0fa0ff507f01053aeffffffff01c8af0000000000001976a91458b7a60f11a904feef35a639b6048de8dd4d9f1c88ac00000000")  # nopep8

    sig_script = txn.inputs[0].script
    redeem_script = Script(sig_script.ast[-1][-1])
    script_pub_key = Script.build_p2sh(redeem_script.hash160())

    si = ScriptInterpreter(txn=txn,
                           input_index=0,
                           sub_script=redeem_script)
    si.run_script(sig_script)
    assert len(si.stack) == 4
    si.run_script(script_pub_key)
    assert len(si.stack) == 4
    assert si.stack[-1] is True
    assert si.valid
    si._op_verify()

    # This will do the OP_CHECKMULTISIG
    si.run_script(redeem_script)
    assert len(si.stack) == 1
    assert si.stack[0] is True

    assert si.valid
    assert len(si.stack) == 1


def test_op_checklocktimeverify():
    prev_txn_hash = Hash('6eae1e03964799c4e29039db459ea4fad4df57c2b06f730b60032a48fb075620')
    txn_input = TransactionInput(prev_txn_hash, 0, Script(""), 1)

    addr = "1HJiL6AYYmtkbJzC9bxAorznWijwNK5Z8E"
    out_script_pub_key = Script.build_p2pkh(
        utils.address_to_key_hash(addr)[1])
    txn_output = TransactionOutput(9000, out_script_pub_key)

    # Create the txn
    txn = Transaction(Transaction.DEFAULT_TRANSACTION_VERSION,
                      [txn_input],
                      [txn_output],
                      367987)

    # This is one more (367988) so it should fail
    s = Script("0x749d05 OP_CHECKLOCKTIMEVERIFY")

    si = ScriptInterpreter(txn=txn,
                           input_index=0,
                           sub_script=out_script_pub_key)
    si.run_script(s)

    assert not si.valid

    # This is negative, so it should fail
    s = Script("0xfff74d05 OP_CHECKLOCKTIMEVERIFY")

    si = ScriptInterpreter(txn=txn,
                           input_index=0,
                           sub_script=out_script_pub_key)
    si.run_script(s)

    assert not si.valid

    # This is one less (367986) so it should pass
    s = Script("0x729d05 OP_CHECKLOCKTIMEVERIFY")

    si = ScriptInterpreter(txn=txn,
                           input_index=0,
                           sub_script=out_script_pub_key)
    si.run_script(s)

    assert not si.stop

    # Now reformulate the txn so that the input is finalized
    txn_input.sequence_num = 0xffffffff
    si.run_script(s)

    assert not si.valid

    # The last check is if there are mismatching notions of locktime
    txn_input.sequence_num = 1
    txn.lock_time = 500000001
    si = ScriptInterpreter(txn=txn,
                           input_index=0,
                           sub_script=out_script_pub_key)
    si.run_script(s)

    assert not si.valid


def test_disabled_ops():
    for opcode in ScriptInterpreter.DISABLED_OPS:
        si = ScriptInterpreter()
        si.run_script(Script("OP_1 " + opcode + " OP_2"))

        assert not si.valid
        assert list(si.stack) == [1]


def test_stack_overflow():
    s = Script("OP_0 " * 1001 + "OP_1")

    si = ScriptInterpreter()
    with pytest.raises(ScriptInterpreterError):
        si.run_script(s)
