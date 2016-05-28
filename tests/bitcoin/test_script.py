import pytest

from two1.bitcoin.exceptions import ScriptParsingError
from two1.bitcoin.script import Script
from two1.bitcoin.txn import Transaction
from two1.bitcoin.utils import bytes_to_str, pack_var_str


def test_serialization():
    scr = 'OP_ADD OP_IF OP_DUP OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY OP_CHECKSIG OP_ELSE OP_IF OP_DUP OP_ELSE OP_2ROT OP_ENDIF OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUAL OP_ENDIF 0x010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101010101'    # nopep8

    s = Script(scr)
    assert s._tokens == ['OP_ADD', 'OP_IF', 'OP_DUP', 'OP_HASH160', b'h\xbf\x82z/\xa3\xb3\x1eS!^]\xd1\x92`\xd2\x1f\xdf\x05>', 'OP_EQUALVERIFY', 'OP_CHECKSIG', 'OP_ELSE', 'OP_IF', 'OP_DUP', 'OP_ELSE', 'OP_2ROT', 'OP_ENDIF', 'OP_HASH160', b'h\xbf\x82z/\xa3\xb3\x1eS!^]\xd1\x92`\xd2\x1f\xdf\x05>', 'OP_EQUAL', 'OP_ENDIF',  b'\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01']    # nopep8

    s_bytes = bytes(s)
    s_hex_str = bytes_to_str(s_bytes)

    s1 = Script.from_bytes(pack_var_str(s_bytes))[0]
    assert bytes(s1) == s_bytes

    raw_scr = "483045022100d60baf72dbaed8d15c3150e3309c9f7725fbdf91b0560330f3e2a0ccb606dfba02206422b1c73ce390766f0dc4e9143d0fbb400cc207e4a9fd9130e7f79e52bf81220121034ccd52d8f72cfdd680077a1a171458a1f7574ebaa196095390ae45e68adb3688"  # nopep8
    s = Script(bytes.fromhex(raw_scr))
    s._check_tokenized()
    assert s._tokens
    assert s._ast

    s_hex_str = bytes_to_str(bytes(s))
    assert s_hex_str == raw_scr

    s = Script('OP_0 OP_IF 0x1337c0de OP_ENDIF OP_1')
    b = bytes.fromhex("0063041337c0de6851")
    s1 = Script.from_bytes(pack_var_str(b))[0]
    assert bytes(s) == b
    assert bytes(s) == bytes(s1)


def test_validate_template():
    template = ['OP_HASH160', bytes, 'OP_EQUALVERIFY', 'OP_CHECKSIG']
    scr = Script('OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY OP_NOP')

    assert not Script.validate_template(scr, template)

    scr[-1] = 'OP_CHECKSIG'

    assert Script.validate_template(scr, template)


def test_remove_op():
    scr = "OP_ADD OP_CODESEPARATOR OP_DUP OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY OP_CHECKSIG"  # nopep8
    s = Script(scr)
    s1 = s.remove_op("OP_CODESEPARATOR")
    assert str(s1) == "OP_ADD OP_DUP OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY OP_CHECKSIG"

    s2 = s1.remove_op("OP_DUP")
    assert str(s2) == "OP_ADD OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY OP_CHECKSIG"

    s3 = s2.remove_op("OP_EQUAL")
    assert str(s2) == str(s3)


def test_list_operations():
    s = Script('OP_0 OP_1 OP_2')
    assert s[0] == 'OP_0'

    del s[2]
    assert s._tokens == ['OP_0', 'OP_1']

    s.append('OP_3')
    assert str(s) == 'OP_0 OP_1 OP_3'

    s.insert(2, 'OP_2')
    assert s._tokens == ['OP_0', 'OP_1', 'OP_2', 'OP_3']
    assert s._ast == ['OP_0', 'OP_1', 'OP_2', 'OP_3']

    for i, o in enumerate(s):
        assert o == 'OP_%d' % i

    s = Script('OP_1 OP_IF OP_2 OP_ELSE OP_3 OP_ENDIF')
    with pytest.raises(ScriptParsingError):
        del s[1]

    s = Script('OP_1 OP_IF OP_2 OP_ELSE OP_3 OP_ENDIF')
    del s[3]
    assert s._tokens == ['OP_1', 'OP_IF', 'OP_2', 'OP_3', 'OP_ENDIF']
    assert len(s) == 5
    assert str(s) == 'OP_1 OP_IF OP_2 OP_3 OP_ENDIF'

    s = Script('OP_1 OP_IF OP_2 OP_ELSE OP_3 OP_ENDIF')
    with pytest.raises(ScriptParsingError):
        del s[5]

    s = Script(['OP_1', 'OP_3'])
    assert len(s) == 2
    assert s._tokens == ['OP_1', 'OP_3']


def test_multisig():
    # This test-case taken from:
    # https://gist.github.com/gavinandresen/3966071
    pubkeys = [
        "0491bba2510912a5bd37da1fb5b1673010e43d2c6d812c514e91bfa9f2eb129e1c183329db55bd868e209aac2fbc02cb33d98fe74bf23f0c235d6126b1d8334f86",  # nopep8
        "04865c40293a680cb9c020e7b1e106d8c1916d3cef99aa431a56d253e69256dac09ef122b1a986818a7cb624532f062c1d1f8722084861c5c3291ccffef4ec6874",  # nopep8
        "048d2455d2403e08708fc1f556002f1b6cd83f992d085097f9974ab08a28838f07896fbab08f39495e15fa6fad6edbfb1e754e35fa1c7844c41f322a1863d46213"]  # nopep8

    serialized_pubkeys = [bytes.fromhex(p) for p in pubkeys]

    redeem_script = Script.build_multisig_redeem(2, serialized_pubkeys)

    assert bytes_to_str(bytes(redeem_script)) == "52410491bba2510912a5bd37da1fb5b1673010e43d2c6d812c514e91bfa9f2eb129e1c183329db55bd868e209aac2fbc02cb33d98fe74bf23f0c235d6126b1d8334f864104865c40293a680cb9c020e7b1e106d8c1916d3cef99aa431a56d253e69256dac09ef122b1a986818a7cb624532f062c1d1f8722084861c5c3291ccffef4ec687441048d2455d2403e08708fc1f556002f1b6cd83f992d085097f9974ab08a28838f07896fbab08f39495e15fa6fad6edbfb1e754e35fa1c7844c41f322a1863d4621353ae"  # nopep8

    assert redeem_script.is_multisig_redeem()

    # Get the address of the redeem script
    assert redeem_script.address(True).startswith("2")
    address = redeem_script.address()
    assert address == "3QJmV3qfvL9SuYo34YihAf3sRCW3qSinyC"


def test_is_p2pkh():
    s = Script("OP_DUP OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY OP_CHECKSIG")
    assert s.is_p2pkh()
    assert not s.is_multisig_redeem()
    assert not s.is_p2pkh_sig()

    assert s.address()

    addresses = s.get_addresses()
    assert len(addresses) == 1
    assert addresses[0] == '1AYrhH1SAQqhT8w5NguBSogN63ajS6PxNL'

    s = Script.build_p2pkh(bytes.fromhex("68bf827a2fa3b31e53215e5dd19260d21fdf053e"))
    assert s.is_p2pkh()

    s = Script("OP_ADD OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY")
    assert not s.is_p2pkh()
    assert not s.is_multisig_redeem()


def test_is_p2pkh_sig():
    t = Transaction.from_hex("0100000001205607fb482a03600b736fb0c257dfd4faa49e45db3990e2c4994796031eae6e000000008b483045022100ed84be709227397fb1bc13b749f235e1f98f07ef8216f15da79e926b99d2bdeb02206ff39819d91bc81fecd74e59a721a38b00725389abb9cbecb42ad1c939fd8262014104e674caf81eb3bb4a97f2acf81b54dc930d9db6a6805fd46ca74ac3ab212c0bbf62164a11e7edaf31fbf24a878087d925303079f2556664f3b32d125f2138cbefffffffff0128230000000000001976a914f1fd1dc65af03c30fe743ac63cef3a120ffab57d88ac00000000")  # nopep8

    assert t.inputs[0].script.is_p2pkh_sig()

    sig_info = t.inputs[0].script.extract_sig_info()
    assert bytes_to_str(sig_info['public_key']) == '04e674caf81eb3bb4a97f2acf81b54dc930d9db6a6805fd46ca74ac3ab212c0bbf62164a11e7edaf31fbf24a878087d925303079f2556664f3b32d125f2138cbef'  # nopep8

    input_addresses = t.inputs[0].script.get_addresses()
    assert len(input_addresses) == 1
    assert input_addresses[0] == '1NKxQnbtKDdL6BY1UaKdrzCxQHfn3TQnqZ'


def test_is_p2sh():
    s = Script("OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUAL")
    assert s.is_p2sh()
    assert not s.is_multisig_redeem()
    assert not s.is_p2pkh_sig()

    s = Script.build_p2sh(bytes.fromhex("68bf827a2fa3b31e53215e5dd19260d21fdf053e"))
    assert s.is_p2sh()

    s = Script("OP_ADD OP_HASH160 0x68bf827a2fa3b31e53215e5dd19260d21fdf053e OP_EQUALVERIFY")
    assert not s.is_p2sh()
    assert not s.is_multisig_redeem()


def test_multisig_sig():
    sig_script = Script('OP_0 0x30440220762ce7bca626942975bfd5b130ed3470b9f538eb2ac120c2043b445709369628022051d73c80328b543f744aa64b7e9ebefa7ade3e5c716eab4a09b408d2c307ccd701 0x3045022100abf740b58d79cab000f8b0d328c2fff7eb88933971d1b63f8b99e89ca3f2dae602203354770db3cc2623349c87dea7a50cee1f78753141a5052b2d58aeb592bcf50f01 0x524104a882d414e478039cd5b52a92ffb13dd5e6bd4515497439dffd691a0f12af9575fa349b5694ed3155b136f09e63975a1700c9f4d4df849323dac06cf3bd6458cd41046ce31db9bdd543e72fe3039a1f1c047dab87037c36a669ff90e28da1848f640de68c2fe913d363a51154a0c62d7adea1b822d05035077418267b1a1379790187410411ffd36c70776538d079fbae117dc38effafb33304af83ce4894589747aee1ef992f63280567f52f5ba870678b4ab4ff6c8ea600bd217870a8b4f1f09f3a8e8353ae')  # nopep8

    assert sig_script.is_multisig_sig()

    r = sig_script.extract_multisig_sig_info()
    redeem_info = r['redeem_script'].extract_multisig_redeem_info()
    assert len(r['signatures']) == 2
    assert r['redeem_script']
    assert isinstance(r['redeem_script'], Script)

    s = Script.build_multisig_sig(r['signatures'], r['redeem_script'])
    assert bytes(s) == bytes(sig_script)

    # This is a test case where there is no OP_PUSHDATA
    raw_scr = "00483045022100fa1225f8828fd6fe52665c3c4258169a84af52b41525f2e288082f174c032f47022022758d5519db3ab2cec4a330e96568b9289fb77c5653bce49397df01a3fcff5101475221038b5fa60aee4c4e9ab3a66e6bb32211a54da6b054c6143dd221c122ce936315d921023180e1b49b7f3fd1254a19c7aa8016ad995089b99c9dac89752cd17e40d9072d52ae"  # nopep8
    s, _ = Script.from_bytes(pack_var_str(bytes.fromhex(raw_scr)))

    assert sig_script.is_multisig_sig()

    r = s.extract_multisig_sig_info()
    assert len(r['signatures']) == 1
    assert r['redeem_script']
    assert isinstance(r['redeem_script'], Script)

    sig_addresses = sig_script.get_addresses()
    assert len(sig_addresses) == redeem_info['n'] + 1
    assert sig_addresses == ['1JzVFZSN1kxGLTHG41EVvY5gHxLAX7q1Rh',
                             '14JfSvgEq8A8S7qcvxeaSCxhn1u1L71vo4',
                             '1Kyy7pxzSKG75L9HhahRZgYoer9FePZL4R',
                             '347N1Thc213QqfYCz3PZkjoJpNv5b14kBd']
