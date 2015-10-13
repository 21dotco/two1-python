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

    redeem_script = Script.build_multisig_redeem(2, serialized_pubkeys)

    assert bytes_to_str(bytes(redeem_script)) == "52410491bba2510912a5bd37da1fb5b1673010e43d2c6d812c514e91bfa9f2eb129e1c183329db55bd868e209aac2fbc02cb33d98fe74bf23f0c235d6126b1d8334f864104865c40293a680cb9c020e7b1e106d8c1916d3cef99aa431a56d253e69256dac09ef122b1a986818a7cb624532f062c1d1f8722084861c5c3291ccffef4ec687441048d2455d2403e08708fc1f556002f1b6cd83f992d085097f9974ab08a28838f07896fbab08f39495e15fa6fad6edbfb1e754e35fa1c7844c41f322a1863d4621353ae"

    assert redeem_script.is_multisig_redeem()

    # Get the address of the redeem script
    assert redeem_script.address(True).startswith("2")
    address = redeem_script.address()
    assert address == "3QJmV3qfvL9SuYo34YihAf3sRCW3qSinyC"


def test_is_p2pkh():
    s = Script("OP_DUP OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY OP_CHECKSIG")
    assert s.is_p2pkh()
    assert not s.is_multisig_redeem()

    assert not s.address()

    s = Script.build_p2pkh(bytes.fromhex("68bf827a2fa3b31e53215e5dd19260d21fdf053e"))
    assert s.is_p2pkh()
    
    s = Script("OP_ADD OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY")
    assert not s.is_p2pkh()
    assert not s.is_multisig_redeem()


def test_is_p2sh():
    s = Script("OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUAL")
    assert s.is_p2sh()
    assert not s.is_multisig_redeem()

    s = Script.build_p2sh(bytes.fromhex("68bf827a2fa3b31e53215e5dd19260d21fdf053e"))
    assert s.is_p2sh()

    s = Script("OP_ADD OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY")
    assert not s.is_p2sh()
    assert not s.is_multisig_redeem()


def test_multisig_sig():
    sig_script = Script('OP_0 0x30440220762ce7bca626942975bfd5b130ed3470b9f538eb2ac120c2043b445709369628022051d73c80328b543f744aa64b7e9ebefa7ade3e5c716eab4a09b408d2c307ccd701 0x3045022100abf740b58d79cab000f8b0d328c2fff7eb88933971d1b63f8b99e89ca3f2dae602203354770db3cc2623349c87dea7a50cee1f78753141a5052b2d58aeb592bcf50f01 OP_PUSHDATA1 0xc9 0x524104a882d414e478039cd5b52a92ffb13dd5e6bd4515497439dffd691a0f12af9575fa349b5694ed3155b136f09e63975a1700c9f4d4df849323dac06cf3bd6458cd41046ce31db9bdd543e72fe3039a1f1c047dab87037c36a669ff90e28da1848f640de68c2fe913d363a51154a0c62d7adea1b822d05035077418267b1a1379790187410411ffd36c70776538d079fbae117dc38effafb33304af83ce4894589747aee1ef992f63280567f52f5ba870678b4ab4ff6c8ea600bd217870a8b4f1f09f3a8e8353ae')

    assert sig_script.is_multisig_sig()

    r = sig_script.extract_multisig_sig_info()
    assert len(r['signatures']) == 2
    assert r['redeem_script']
    assert isinstance(r['redeem_script'], Script)

    s = Script.build_multisig_sig(r['signatures'], r['redeem_script'])
    assert bytes(s) == bytes(sig_script)

    # This is a test case where there is no OP_PUSHDATA
    raw_scr = "00483045022100fa1225f8828fd6fe52665c3c4258169a84af52b41525f2e288082f174c032f47022022758d5519db3ab2cec4a330e96568b9289fb77c5653bce49397df01a3fcff5101475221038b5fa60aee4c4e9ab3a66e6bb32211a54da6b054c6143dd221c122ce936315d921023180e1b49b7f3fd1254a19c7aa8016ad995089b99c9dac89752cd17e40d9072d52ae"
    s, _ = Script.from_bytes(pack_var_str(bytes.fromhex(raw_scr)))

    assert sig_script.is_multisig_sig()

    r = s.extract_multisig_sig_info()
    assert len(r['signatures']) == 1
    assert r['redeem_script']
    assert isinstance(r['redeem_script'], Script)
