import base58

from two1.lib.bitcoin.script import Script
from two1.lib.bitcoin.utils import bytes_to_str, pack_var_str


def test_serialization():
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


def test_remove_op():
    scr = "OP_ADD OP_CODESEPARATOR OP_DUP OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY OP_CHECKSIG"
    s = Script(scr)
    s1 = s.remove_op("OP_CODESEPARATOR")
    assert str(s1) == "OP_ADD OP_DUP OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY OP_CHECKSIG"

    s2 = s1.remove_op("OP_DUP")
    assert str(s2) == "OP_ADD OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY OP_CHECKSIG"

    s3 = s2.remove_op("OP_EQUAL")
    assert str(s2) == str(s3)


def test_multisig():
    # This test-case taken from:
    # https://gist.github.com/gavinandresen/3966071
    pubkeys = ["0491bba2510912a5bd37da1fb5b1673010e43d2c6d812c514e91bfa9f2eb129e1c183329db55bd868e209aac2fbc02cb33d98fe74bf23f0c235d6126b1d8334f86",
               "04865c40293a680cb9c020e7b1e106d8c1916d3cef99aa431a56d253e69256dac09ef122b1a986818a7cb624532f062c1d1f8722084861c5c3291ccffef4ec6874",
               "048d2455d2403e08708fc1f556002f1b6cd83f992d085097f9974ab08a28838f07896fbab08f39495e15fa6fad6edbfb1e754e35fa1c7844c41f322a1863d46213"]

    serialized_pubkeys = [bytes.fromhex(p) for p in pubkeys]

    ret = Script.build_multisig(2, serialized_pubkeys)

    assert bytes_to_str(bytes(ret['redeemScript'])) == "52410491bba2510912a5bd37da1fb5b1673010e43d2c6d812c514e91bfa9f2eb129e1c183329db55bd868e209aac2fbc02cb33d98fe74bf23f0c235d6126b1d8334f864104865c40293a680cb9c020e7b1e106d8c1916d3cef99aa431a56d253e69256dac09ef122b1a986818a7cb624532f062c1d1f8722084861c5c3291ccffef4ec687441048d2455d2403e08708fc1f556002f1b6cd83f992d085097f9974ab08a28838f07896fbab08f39495e15fa6fad6edbfb1e754e35fa1c7844c41f322a1863d4621353ae"

    hash160 = bytes.fromhex(ret['pubKeyScript'].get_hash160()[2:])

    # Script hash addresses are prepended with 5 rather 0
    address = base58.b58encode_check(bytes([0x05]) + hash160)

    assert address == "3QJmV3qfvL9SuYo34YihAf3sRCW3qSinyC"
