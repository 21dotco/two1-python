import pytest
from two1.bitcoin import crypto, hash, script, txn, utils

# The first key in this list had 10000 satoshis sent to it in block 369023
keys = [(crypto.PrivateKey.from_b58check('5JcjcDkFZ3Dz4RjnK3n9cyLVmNS3FzGdNRtNMGFBfJKgzM8eAhH'),
         crypto.PublicKey(0xe674caf81eb3bb4a97f2acf81b54dc930d9db6a6805fd46ca74ac3ab212c0bbf,
                          0x62164a11e7edaf31fbf24a878087d925303079f2556664f3b32d125f2138cbef)),
        (crypto.PrivateKey.from_b58check('5KK5GkzYJKa7evzYPdvDPmB9XWaKQY9qJS5ouRx4ndBHNHbb2Hq'),
         crypto.PublicKey(0x5866260447c0adfdb26dbe5060a7a298e17d051008ce1677d19fe3d3373284b9,
                          0xc384a3445dd96f96c11d3b33d82083e9ecc27d0abfa9fd433afaa5006186bf61))]


@pytest.mark.parametrize("keypair", keys)
def test_key_addresses(keypair):
    private_key, public_key = keypair
    assert private_key.public_key.point == public_key.point


@pytest.mark.parametrize("message, keypair, exp_sig", [
    (b"Hello, World!!", keys[0],
     "G1axea+IdcHXdLH6mO5RLLFpwfLHq0aeCio2IBkntGPrBYKuLybWBoF/ZUivx179qGUU9/1kv9GND9sLvsSBlzw="),
    (b"Hello, World!!!", keys[0],
     "HF9Q4TQMXGhjPeugn852A1WogZOGx2MOL5eMgHryTdkMZCKmCNzjHk4Lmi+sUWv9ekimLtBSiqkfjmoyUo1qzgM="),
    (b"The dog is brown.", keys[0],
     "HNiO1y7/h+Y+YfKfmubK40jnwraR3FDA7R3Ne42lML1MfIdcXMNvCrUMsONjDSuOqvft8YmIE8sQ/9S2pb+rL7Y="),
    (b"blah blah blah", keys[0],
     "G4IYxSa+GyV+yzxOrJw7hhc/QyWjaC0fhHx0FQhyfdfLWc4JURK1c23naiX+X1uuPA7PHLfbSaKKoHujbdLqS+Y="),
    ])
def test_bitcoin_message_signing(message, keypair, exp_sig):
    private_key, public_key = keypair

    sig_b64 = private_key.sign_bitcoin(message)
    address = public_key.address(compressed=False)
    print("Verify with bx:")
    print("bx message-validate %s %s '%s'" % (address,
                                              sig_b64.decode('ascii'),
                                              message.decode('ascii')))
    print()

    assert sig_b64.decode('ascii') == exp_sig

    # Check to make sure the recovered public key is correct
    assert crypto.PublicKey.verify_bitcoin(message, sig_b64, address)


def test_sign_txn():
    # Let's create a txn trying to spend one of Satoshi's coins: block 1
    # We make the (false) assertion that we own the private key (private_key1)
    # and for a raw txn, we put the scriptPubKey associated with that private key
    address1 = keys[0][1].address(compressed=False)
    address2 = keys[1][1].address(compressed=False)

    # Real txn in block 369023 to keys[0]
    prev_txn_hash = hash.Hash('6eae1e03964799c4e29039db459ea4fad4df57c2b06f730b60032a48fb075620')
    prev_script_pub_key = script.Script.build_p2pkh(utils.address_to_key_hash(address1)[1])
    txn_input = txn.TransactionInput(prev_txn_hash,
                                     0,
                                     script.Script(""),
                                     0xffffffff)

    # Build the output so that it pays out to address2
    out_script_pub_key = script.Script.build_p2pkh(utils.address_to_key_hash(address2)[1])
    txn_output = txn.TransactionOutput(9000, out_script_pub_key)  # 1000 satoshi fee

    # Create the txn
    transaction = txn.Transaction(txn.Transaction.DEFAULT_TRANSACTION_VERSION,
                                  [txn_input],
                                  [txn_output],
                                  0)

    # Now sign input 0 (there is only 1)
    transaction.sign_input(0, txn.Transaction.SIG_HASH_ALL, keys[0][0], prev_script_pub_key)

    # Dump it out as hex
    signed_txn_hex = transaction.to_hex()

    # The above txn was submitted via bitcoin-cli.
    # See: https://www.blocktrail.com/BTC/tx/695f0b8605cc8a117c3fe5b959e6ee2fabfa49dcc615ac496b5dd114105cd360
    assert signed_txn_hex == "0100000001205607fb482a03600b736fb0c257dfd4faa49e45db3990e2c4994796031eae6e000000008b483045022100ed84be709227397fb1bc13b749f235e1f98f07ef8216f15da79e926b99d2bdeb02206ff39819d91bc81fecd74e59a721a38b00725389abb9cbecb42ad1c939fd8262014104e674caf81eb3bb4a97f2acf81b54dc930d9db6a6805fd46ca74ac3ab212c0bbf62164a11e7edaf31fbf24a878087d925303079f2556664f3b32d125f2138cbefffffffff0128230000000000001976a914f1fd1dc65af03c30fe743ac63cef3a120ffab57d88ac00000000"  # nopep8

    assert transaction.verify_input_signature(0, prev_script_pub_key)
    assert not transaction.verify_input_signature(0, out_script_pub_key)


def test_multisig_sign():
    # This test case taken from:
    # https://github.com/libbitcoin/libbitcoin-explorer/wiki/How-to-Spend-From-a-Multisig-Address

    unsigned_hex = "01000000010506344de69d47e432eb0174500d6e188a9e63c1e84a9e8796ec98c99b7559f70100000000ffffffff01c8af0000000000001976a91458b7a60f11a904feef35a639b6048de8dd4d9f1c88ac00000000"  # nopep8

    tx = txn.Transaction.from_hex(unsigned_hex)

    pub_keys_hex = ["02b66fcb1064d827094685264aaa90d0126861688932eafbd1d1a4ba149de3308b",
                    "025cab5e31095551582630f168280a38eb3a62b0b3e230b20f8807fc5463ccca3c",
                    "021098babedb3408e9ac2984adcf2a8e4c48e56a785065893f76d0fa0ff507f010"]
    pub_keys = [bytes.fromhex(p) for p in pub_keys_hex]
    redeem_script = script.Script.build_multisig_redeem(2, pub_keys)
    script.Script.build_p2sh(
        bytes.fromhex("5c406de4915e37a7e71c7ef9bff42fbf1404daa0"))

    priv_keys_hex = ["0x9d695afea1c3ab99e11248e4b74e698332b11f5c5c051e6e80da61aa19ae7c89",
                     "0x68ebab45a918444d7e088c49bda76d7df89b9ea6ba5ddeb1aab5945391828b83"]
    priv_keys = [crypto.PrivateKey.from_int(int(p, 0))
                 for p in priv_keys_hex]

    # Now sign the input with the first private key
    tx.sign_input(input_index=0,
                  hash_type=txn.Transaction.SIG_HASH_ALL,
                  private_key=priv_keys[0],
                  sub_script=redeem_script)

    # Check the sig script
    assert utils.bytes_to_str(tx.inputs[0].script.ast[1]) == "30440220695a28c42daa23c13e192e36a20d03a2a79994e0fe1c3c6b612d0ae23743064602200ca19003e7c1ce0cecb0bbfba9a825fc3b83cf54e4c3261cd15f080d24a8a5b901"  # nopep8

    # Now sign with the second private key
    tx.sign_input(input_index=0,
                  hash_type=txn.Transaction.SIG_HASH_ALL,
                  private_key=priv_keys[1],
                  sub_script=redeem_script)

    assert utils.bytes_to_str(tx.inputs[0].script.ast[2]) == "3045022100aa9096ce71995c24545694f20ab0482099a98c99b799c706c333c521e51db66002206578f023fa46f4a863a6fa7f18b95eebd1a91fcdf6ce714e8795d902bd6b682b01"  # nopep8

    # Now make sure the entire serialized txn is correct
    assert tx.to_hex() == "01000000010506344de69d47e432eb0174500d6e188a9e63c1e84a9e8796ec98c99b7559f701000000fdfd00004730440220695a28c42daa23c13e192e36a20d03a2a79994e0fe1c3c6b612d0ae23743064602200ca19003e7c1ce0cecb0bbfba9a825fc3b83cf54e4c3261cd15f080d24a8a5b901483045022100aa9096ce71995c24545694f20ab0482099a98c99b799c706c333c521e51db66002206578f023fa46f4a863a6fa7f18b95eebd1a91fcdf6ce714e8795d902bd6b682b014c69522102b66fcb1064d827094685264aaa90d0126861688932eafbd1d1a4ba149de3308b21025cab5e31095551582630f168280a38eb3a62b0b3e230b20f8807fc5463ccca3c21021098babedb3408e9ac2984adcf2a8e4c48e56a785065893f76d0fa0ff507f01053aeffffffff01c8af0000000000001976a91458b7a60f11a904feef35a639b6048de8dd4d9f1c88ac00000000"  # nopep8

    script_pub_key = script.Script.build_p2sh(redeem_script.hash160())
    assert tx.verify_input_signature(0, script_pub_key)

    assert not tx.verify_input_signature(0, redeem_script)

    wrong_script_pub_key = script.Script(
        "OP_HASH160 0x5c406de4915e37a7e71c7ef9bff42fbf1404daa1 OP_EQUAL")
    assert not tx.verify_input_signature(0, wrong_script_pub_key)

    # Test not enough signatures
    tx = txn.Transaction.from_hex(unsigned_hex)

    # Sign the input with only the first private key
    tx.sign_input(input_index=0,
                  hash_type=txn.Transaction.SIG_HASH_ALL,
                  private_key=priv_keys[0],
                  sub_script=redeem_script)

    assert not tx.verify_input_signature(0, script_pub_key)

    # Try doing it with the 2nd private key but not the first
    tx = txn.Transaction.from_hex(unsigned_hex)
    tx.sign_input(input_index=0,
                  hash_type=txn.Transaction.SIG_HASH_ALL,
                  private_key=priv_keys[1],
                  sub_script=redeem_script)

    assert not tx.verify_input_signature(0, script_pub_key)

    # Now try doing the sigs in reverse order
    tx = txn.Transaction.from_hex(unsigned_hex)
    tx.sign_input(input_index=0,
                  hash_type=txn.Transaction.SIG_HASH_ALL,
                  private_key=priv_keys[1],
                  sub_script=redeem_script)
    tx.sign_input(input_index=0,
                  hash_type=txn.Transaction.SIG_HASH_ALL,
                  private_key=priv_keys[0],
                  sub_script=redeem_script)

    # This should still work
    assert tx.verify_input_signature(0, script_pub_key)
    # The partial should also work
    assert tx.verify_partial_multisig(0, script_pub_key)

    # Now hack the txn bytes to have the sigs in reverse order.
    # This should fail.
    txn_hex = "01000000010506344de69d47e432eb0174500d6e188a9e63c1e84a9e8796ec98c99b7559f701000000fdfd0000483045022100aa9096ce71995c24545694f20ab0482099a98c99b799c706c333c521e51db66002206578f023fa46f4a863a6fa7f18b95eebd1a91fcdf6ce714e8795d902bd6b682b014730440220695a28c42daa23c13e192e36a20d03a2a79994e0fe1c3c6b612d0ae23743064602200ca19003e7c1ce0cecb0bbfba9a825fc3b83cf54e4c3261cd15f080d24a8a5b9014c69522102b66fcb1064d827094685264aaa90d0126861688932eafbd1d1a4ba149de3308b21025cab5e31095551582630f168280a38eb3a62b0b3e230b20f8807fc5463ccca3c21021098babedb3408e9ac2984adcf2a8e4c48e56a785065893f76d0fa0ff507f01053aeffffffff01c8af0000000000001976a91458b7a60f11a904feef35a639b6048de8dd4d9f1c88ac00000000"  # nopep8

    tx = txn.Transaction.from_hex(txn_hex)

    assert not tx.verify_input_signature(0, script_pub_key)

    # Test a partially signed txn
    txn_hex = "0100000001124f2e9522043794a438bfa44dd161b8976af246e4850948f85a2b50c113611a000000009200483045022100ec2e3fd3e116eb25644f055ba7945d940f828b39060d4a93c7d2b6d3cbd9d41802203c9f1ad2208122e1ffcbeba09d37a596ae5ce445be465b9417481f66ab804b070147522102395a983fd92e55200fbde624f62cda10f8d0adf8261506e5c983cfe92326c5aa2102bb70b001d807721e74d96bda71d225dc6c09fe8d541d260258145b42afac93e152ae0000000001a0860100000000001976a914e205124b0e25dc77e2b29b2e57c2f56ed10771eb88ac095635ac"  # nopep8

    tx = txn.Transaction.from_hex(txn_hex)

    sig_info = tx.inputs[0].script.extract_multisig_sig_info()
    script_pub_key = script.Script.build_p2sh(sig_info['redeem_script'].hash160())
    assert not tx.verify_input_signature(0, script_pub_key)

    assert tx.verify_partial_multisig(0, script_pub_key)
