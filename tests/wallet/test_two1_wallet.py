import json
import pytest
from pbkdf2 import PBKDF2
import random
import string
import tempfile

from two1.bitcoin.crypto import HDKey, HDPrivateKey
from two1.bitcoin.utils import bytes_to_str
from two1.bitcoin.utils import rand_bytes
from two1.blockchain.mock_provider import MockProvider
from two1.wallet import exceptions
from two1.wallet.two1_wallet import Two1Wallet

enc_key_salt = b'\xaa\xbb\xcc\xdd'
passphrase = "test_wallet"
passphrase_hash = PBKDF2.crypt(passphrase)

master_key = "xprv9s21ZrQH143K2dUcTctuNw8oV8e7gi4ZbHFGAnyGJtWwmKbKTbLGtx48DQGzioGDdhVn8zFhJe8hbDdfDnK19ykxjwXLzd6EpxnTqi4zQGN"  # nopep8
master_seed = "tuna object element cancel hard nose faculty noble swear net subway offer"

mkey_enc, mseed_enc = Two1Wallet.encrypt(master_key=master_key,
                                         master_seed=master_seed,
                                         passphrase=passphrase,
                                         key_salt=enc_key_salt)

config = {'master_key': mkey_enc,
          'master_seed': mseed_enc,
          'locked': True,
          'passphrase_hash': passphrase_hash,
          'key_salt': bytes_to_str(enc_key_salt),
          'account_type': "BIP44BitcoinMainnet",
          'accounts': [{'public_key': "xpub6CNX3TRAXGpoV1a3ai3Hs9R85t63V3k6BGsTaxZZMJJ4DL6kRY8riYA1r6hxyeuxgeb33FfBgrJrV6wxv6VXEVHAfPGJNw8ZzbEJHgsbmpz",  # nopep8
                        'last_payout_index': 2,
                        'last_change_index': 1}],
          'account_map': {'default': 0}}

master = HDPrivateKey.master_key_from_mnemonic(master_seed, passphrase)
mock_provider = MockProvider("BIP44BitcoinMainnet", master)


def test_encrypt_decrypt():
    mkey_enc, mseed_enc = Two1Wallet.encrypt(master_key=config['master_key'],
                                             master_seed=config['master_seed'],
                                             passphrase=passphrase,
                                             key_salt=enc_key_salt)

    mkey, mseed = Two1Wallet.decrypt(master_key_enc=mkey_enc,
                                     master_seed_enc=mseed_enc,
                                     passphrase=passphrase,
                                     key_salt=enc_key_salt)

    assert mkey == config['master_key']
    assert mseed == config['master_seed']

    for i in range(1000):
        s = ''.join(random.choice(string.ascii_letters + string.digits)
                    for _ in range(random.randint(1, 200)))
        key = rand_bytes(Two1Wallet.AES_BLOCK_SIZE)

        enc = Two1Wallet._encrypt_str(s, key)
        dec = Two1Wallet._decrypt_str(enc, key)
        assert dec == s


def test_create():
    # Here we just check to see that the config was created properly,
    # there is only 1 account associated w/the wallet and that there
    # are no txns, etc.

    mock_provider.set_txn_side_effect_for_hd_discovery()

    wallet, _ = Two1Wallet.create(data_provider=mock_provider,
                                  passphrase=passphrase)

    assert len(wallet._accounts) == 1
    assert wallet._accounts[0].name == "default"
    assert wallet._accounts[0].index == 0x80000000

    wallet_config = wallet.to_dict()
    assert wallet_config['account_map'] == {"default": 0}
    assert wallet_config['accounts'][0]['last_payout_index'] == -1
    assert wallet_config['accounts'][0]['last_change_index'] == -1


def test_import():
    m = mock_provider
    m.reset_mocks()

    keys = HDKey.from_path(master, "m/44'/0'/0'")
    m.hd_master_key = master

    m.set_num_used_accounts(0)
    m.set_txn_side_effect_for_hd_discovery()

    wallet = Two1Wallet.import_from_mnemonic(data_provider=m,
                                             mnemonic=master_seed,
                                             passphrase=passphrase,
                                             account_type="BIP44BitcoinMainnet")

    assert wallet._root_keys[1].to_b58check() == keys[1].to_b58check()
    assert wallet._root_keys[2].to_b58check() == keys[2].to_b58check()
    assert wallet._accounts[0].key.to_b58check() == keys[3].to_b58check()

    assert len(wallet._accounts) == 1

    # Now test where the first account has transactions
    m.reset_mocks()
    m.set_num_used_accounts(2)  # Set this to 2 so that we get the side effects
    m.set_num_used_addresses(account_index=0, n=10, change=0)
    m.set_num_used_addresses(account_index=0, n=20, change=1)

    m.set_txn_side_effect_for_hd_discovery()

    wallet = Two1Wallet.import_from_mnemonic(data_provider=m,
                                             mnemonic=master_seed,
                                             passphrase=passphrase,
                                             account_type="BIP44BitcoinMainnet")

    assert len(wallet._accounts) == 1
    assert wallet._accounts[0].has_txns()

    # Test where multiple accounts have transactions
    m.reset_mocks()
    m.set_num_used_accounts(5)
    for i in range(4):
        m.set_num_used_addresses(account_index=i, n=1, change=0)
        m.set_num_used_addresses(account_index=i, n=2, change=1)

    m.set_txn_side_effect_for_hd_discovery()

    wallet = Two1Wallet.import_from_mnemonic(data_provider=m,
                                             mnemonic=master_seed,
                                             passphrase=passphrase,
                                             account_type="BIP44BitcoinMainnet")

    assert len(wallet._accounts) == 4
    for i in range(4):
        assert wallet._accounts[i].has_txns()


def test_rest():
    m = mock_provider
    m.hd_master_key = master
    m.reset_mocks()

    m.set_num_used_accounts(1)
    m.set_num_used_addresses(account_index=0, n=1, change=0)
    m.set_num_used_addresses(account_index=0, n=2, change=1)

    m.set_txn_side_effect_for_hd_discovery()

    wallet = Two1Wallet(params_or_file=config,
                        data_provider=m,
                        passphrase=passphrase)

    # First 5 internal addresses of account 0
    # These can be gotten from https://dcpos.github.io/bip39/
    ext_addrs = ["1Kv1QLXekeE42rKhvZ41kHS1auE7R3t21o",
                 "1CYhVFaBwmTQRQwdyLc4rq9HwaxdqtQ68G",
                 "18KCKKB5MGs4Rqu4t8jL9Bkt9SAp7NpUvm",
                 "1FqUrpUpqWfHoPVga4uMKYCPHHoApvNiPa",
                 "12zb1hJP5WEHCSKz5LyoPM9iaCwXtTthRc"]

    int_addrs = ["1Hiv6LroFmqcaVV9rhY6eNUjnFQh4y6kL7",
                 "1GTUuNbgk4sv7LPQd2WqSP9PiinzeuBmay",
                 "14fpkEZZ6QP3QEcQnfSjH7adkC2RsMuiZw",
                 "1LPNyqqX6RU5b4oPumePR72tFfwiNUho4s",
                 "1FqvNKJb8au82PhtGP8D1odXWVC1Ae4jN9"]

    bad_addrs = ["1CEDwjjtYjCQUoRZQW9RUXHH5Ao7PWYKf",
                 "1CbHFUNsyCzZSDu7hYae7HHqgzMjBfqoP9"]

    paths = wallet.find_addresses(int_addrs + ext_addrs + bad_addrs)

    assert len(paths.keys()) == 10

    for i in range(5):
        # Hardened account key derivation, thus 0x80000000
        assert paths[ext_addrs[i]] == (0x80000000, 0, i)
        assert paths[int_addrs[i]] == (0x80000000, 1, i)

        # Check address belongs
        assert wallet.address_belongs(ext_addrs[i]) == "m/44'/0'/0'/0/%d" % i
        assert wallet.address_belongs(int_addrs[i]) == "m/44'/0'/0'/1/%d" % i

    for b in bad_addrs:
        assert b not in paths
        assert wallet.address_belongs(b) is None

    # Check that there's an account name
    assert wallet.get_account_name(0) == "default"

    # Check the balance
    assert wallet.balances == {'confirmed': 100000, 'total': 200000}

    # Check that we can get a new payout address
    ext_addr = wallet.get_payout_address("default")
    assert ext_addr == ext_addrs[1]
    assert wallet.accounts[0].last_indices[0] == 0

    # Check the balance again - should be the same
    m.set_num_used_addresses(0, 1, 0)
    assert wallet.balances == {'confirmed': 100000, 'total': 200000}

    # Try sending below the dust limit
    with pytest.raises(ValueError):
        wallet.send_to(address="14ocdLGpBp7Yv3gsPDszishSJUv3cpLqUM",
                       amount=544)

    # Try sending a non-integer amount (mistaken user tries to send in btc
    # instead of satoshi)
    with pytest.raises(exceptions.SatoshiUnitsError):
        wallet.send_to(address="14ocdLGpBp7Yv3gsPDszishSJUv3cpLqUM",
                       amount=0.0001)

    # Try sending more than we have and make sure it raises an exception
    with pytest.raises(exceptions.WalletBalanceError):
        wallet.send_to(address="14ocdLGpBp7Yv3gsPDszishSJUv3cpLqUM",
                       amount=10000000)

    # Should still fail when using unconfirmed if amount is greater
    # than unconfirmed balance
    with pytest.raises(exceptions.WalletBalanceError):
        wallet.send_to(address="14ocdLGpBp7Yv3gsPDszishSJUv3cpLqUM",
                       use_unconfirmed=True,
                       amount=10000000)

    # Should fail when not using unconfirmed txns and
    # confirmed < amount < unconfirmed.
    with pytest.raises(exceptions.WalletBalanceError):
        wallet.send_to(address="14ocdLGpBp7Yv3gsPDszishSJUv3cpLqUM",
                       use_unconfirmed=False,
                       amount=150000)

    # Should get past checking balance but raise a NotImplementedError
    with pytest.raises(NotImplementedError):
        wallet.send_to(
            address="14ocdLGpBp7Yv3gsPDszishSJUv3cpLqUM",
            use_unconfirmed=False,
            amount=7700)

    # Should get past checking balance but raise a signing error
    with pytest.raises(NotImplementedError):
        wallet.send_to(
            address="14ocdLGpBp7Yv3gsPDszishSJUv3cpLqUM",
            use_unconfirmed=True,
            amount=12581)

    # test number of addresses in spread_utxos
    with pytest.raises(ValueError):
        wallet.spread_utxos(
            threshold=500000,
            num_addresses=0,
            accounts=[])
    with pytest.raises(ValueError):
        wallet.spread_utxos(
            threshold=500000,
            num_addresses=101,
            accounts=[])

    # test units for spread_utxos
    with pytest.raises(exceptions.SatoshiUnitsError):
        wallet.spread_utxos(
            threshold=0.0001,
            num_addresses=1,
            accounts=[])

    # Finally check storing to a file
    params = {}
    with tempfile.NamedTemporaryFile(delete=True) as tf:
        wallet.to_file(tf)

        # Read it back
        tf.seek(0, 0)
        params = json.loads(tf.read().decode('utf-8'))

        # Check that the params match expected
        assert params['master_key'] == config['master_key']
        assert params['master_seed'] == config['master_seed']
        assert params['locked']
        assert params['key_salt'] == bytes_to_str(enc_key_salt)
        assert params['passphrase_hash'] == passphrase_hash
        assert params['account_type'] == "BIP44BitcoinMainnet"
        assert params['account_map']['default'] == 0
        assert len(params['accounts']) == 1
        assert params['accounts'][0]['last_payout_index'] == 0
        assert params['accounts'][0]['last_change_index'] == 1
        assert params['accounts'][0]['public_key'] == config['accounts'][0]['public_key']

        # Now create the wallet from the file
        with pytest.raises(exceptions.PassphraseError):
            w2 = Two1Wallet(params_or_file=tf.name,
                            data_provider=m,
                            passphrase='wrong_pass')

        # Now do with the correct passphrase
        m.set_txn_side_effect_for_hd_discovery()
        w2 = Two1Wallet(params_or_file=tf.name,
                        data_provider=m,
                        passphrase=passphrase)

        assert len(w2.accounts) == 1
        assert not w2._testnet

        acct = w2.accounts[0]
        assert acct.last_indices[0] == 0
        assert acct.last_indices[1] == 1
