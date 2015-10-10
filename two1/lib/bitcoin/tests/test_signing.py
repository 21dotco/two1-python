import base64
import pytest
import hashlib
from two1.lib.bitcoin import crypto, hash, script, txn, utils

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
    (b"Hello, World!!", keys[0], "G1axea+IdcHXdLH6mO5RLLFpwfLHq0aeCio2IBkntGPrBYKuLybWBoF/ZUivx179qGUU9/1kv9GND9sLvsSBlzw="),
    (b"Hello, World!!!", keys[0], "HF9Q4TQMXGhjPeugn852A1WogZOGx2MOL5eMgHryTdkMZCKmCNzjHk4Lmi+sUWv9ekimLtBSiqkfjmoyUo1qzgM="),
    (b"The dog is brown.", keys[0], "HNiO1y7/h+Y+YfKfmubK40jnwraR3FDA7R3Ne42lML1MfIdcXMNvCrUMsONjDSuOqvft8YmIE8sQ/9S2pb+rL7Y="),
    (b"blah blah blah", keys[0], "G4IYxSa+GyV+yzxOrJw7hhc/QyWjaC0fhHx0FQhyfdfLWc4JURK1c23naiX+X1uuPA7PHLfbSaKKoHujbdLqS+Y="),
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

    prev_txn_hash = hash.Hash('6eae1e03964799c4e29039db459ea4fad4df57c2b06f730b60032a48fb075620') # Real txn in block 369023 to keys[0]
    prev_script_pub_key = script.Script.build_p2pkh(utils.address_to_key_hash(address1)[1])
    txn_input = txn.TransactionInput(prev_txn_hash,
                                     0,
                                     script.Script(""),
                                     0xffffffff)

    # Build the output so that it pays out to address2
    out_script_pub_key = script.Script.build_p2pkh(utils.address_to_key_hash(address2)[1])
    txn_output = txn.TransactionOutput(9000, out_script_pub_key) # 1000 satoshi fee

    # Create the txn
    transaction = txn.Transaction(txn.Transaction.DEFAULT_TRANSACTION_VERSION,
                                  [txn_input],
                                  [txn_output],
                                  0)

    # Now sign input 0 (there is only 1)
    transaction.sign_input(0, txn.Transaction.SIG_HASH_ALL, keys[0][0], prev_script_pub_key)

    # Dump it out as hex
    signed_txn_hex = utils.bytes_to_str(bytes(transaction))

    # The above txn was submitted via bitcoin-cli.
    # See: https://www.blocktrail.com/BTC/tx/695f0b8605cc8a117c3fe5b959e6ee2fabfa49dcc615ac496b5dd114105cd360
    assert signed_txn_hex == "0100000001205607fb482a03600b736fb0c257dfd4faa49e45db3990e2c4994796031eae6e000000008b483045022100ed84be709227397fb1bc13b749f235e1f98f07ef8216f15da79e926b99d2bdeb02206ff39819d91bc81fecd74e59a721a38b00725389abb9cbecb42ad1c939fd8262014104e674caf81eb3bb4a97f2acf81b54dc930d9db6a6805fd46ca74ac3ab212c0bbf62164a11e7edaf31fbf24a878087d925303079f2556664f3b32d125f2138cbefffffffff0128230000000000001976a914f1fd1dc65af03c30fe743ac63cef3a120ffab57d88ac00000000"

    assert transaction.verify_input_signature(0, prev_script_pub_key)
    assert not transaction.verify_input_signature(0, out_script_pub_key)
