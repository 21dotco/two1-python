import pytest
from unittest.mock import MagicMock

from two1.bitcoin.crypto import HDKey, HDPrivateKey
from two1.bitcoin.txn import Transaction
from two1.wallet.two1_wallet import Two1Wallet
from two1.wallet.mock_txn_data_provider import MockTxnDict, MockTransactionDataProvider

config = {'master_key': "xprv9s21ZrQH143K3But1Hju6Ga2H7dn9CyWz7nfAtdEWLhQZ7GGad7qKm4Btg9yfWgBW1xtfjqimL3zHe3TYQaPPXsQDNWSMinX1HdVG4axX5p",
          'master_seed': "tuna object element cancel hard nose faculty noble swear net subway offer",
          'account_type': "BIP44BitcoinMainnet",
          'accounts': [{ 'public_key': "xpub6CcQGHogi7ch8kCGTUJajqCXSY4HNQUj6seuToEGix9gVzrZjxGx1oJEcu1M6zweE6qxvzpddSMZmFKiXwEvghvG4xArBT2PCQLQ3qt4sZP",
                         'last_payout_index': 2,
                         'last_change_index': 1 }],
          'account_map': { 'default': 0 }}

master = HDPrivateKey.master_key_from_mnemonic(config['master_seed'])
mock_txn_provider = MockTransactionDataProvider("BIP44BitcoinMainnet", master)
    
def test_create():
    # Here we just check to see that the config was created properly,
    # there is only 1 account associated w/the wallet and that there
    # are no txns, etc.

    mock_txn_provider.set_txn_side_effect_for_hd_discovery()

    wallet = Two1Wallet.create(txn_data_provider=mock_txn_provider,
                               passphrase='test_wallet')

    assert len(wallet._accounts) == 1
    assert wallet._accounts[0].name == "default"
    assert wallet._accounts[0].index == 0x80000000
    
    wallet_config = wallet.to_dict()
    assert wallet_config['account_map'] == {"default": 0}
    assert wallet_config['accounts'][0]['last_payout_index'] == -1
    assert wallet_config['accounts'][0]['last_change_index'] == -1

def test_import():
    m = mock_txn_provider
    m.reset_mocks()

    keys = HDKey.from_path(master, "m/44'/0'/0'")
    m.hd_master_key = master

    m.set_num_used_accounts(0)
    m.set_txn_side_effect_for_hd_discovery()

    wallet = Two1Wallet.import_from_mnemonic(txn_data_provider=m,
                                             mnemonic=config['master_seed'],
                                             account_type="BIP44BitcoinMainnet")

    assert wallet._root_keys[1].to_b58check() == keys[1].to_b58check()
    assert wallet._root_keys[2].to_b58check() == keys[2].to_b58check()
    assert wallet._accounts[0].key.to_b58check() == keys[3].to_b58check()
    
    assert len(wallet._accounts) == 1

    # Now test where the first account has transactions
    m.reset_mocks()
    m.set_num_used_accounts(2) # Set this to 2 so that we get the side effects
    m.set_num_used_addresses(account_index=0, n=10, change=0)
    m.set_num_used_addresses(account_index=0, n=20, change=1)
    
    m.set_txn_side_effect_for_hd_discovery()

    wallet = Two1Wallet.import_from_mnemonic(txn_data_provider=m,
                                             mnemonic=config['master_seed'],
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

    wallet = Two1Wallet.import_from_mnemonic(txn_data_provider=m,
                                             mnemonic=config['master_seed'],
                                             account_type="BIP44BitcoinMainnet")

    assert len(wallet._accounts) == 4
    for i in range(4):
        assert wallet._accounts[i].has_txns()
        assert len(wallet._accounts[i]._txns.keys()) == 3

def test_rest():
    m = mock_txn_provider
    m.reset_mocks()

    m.set_num_used_accounts(1)
    m.set_num_used_addresses(account_index=0, n=1, change=0)
    m.set_num_used_addresses(account_index=0, n=2, change=1)

    m.set_txn_side_effect_for_hd_discovery()
    
    wallet = Two1Wallet(config=config, txn_data_provider=m)

    # First 5 internal addresses of account 0
    int_addrs = ["12q2xjqTh6ZNHUTQLWSs9uSyDkGHNpQAzu",
                 "1NpksrEeUpMcbw6ekWPZfPd3qAhEL5ygJ4",
                 "1BruaiE6VNXQdeDdhGKhB1x8sq2NcJrDBX",
                 "1ECsMhxMnHR7mMjaP1yBRhUNaUszZUYQUj",
                 "1KbGXnyg1gXx4CA3YnCmpKH252jw8pR9C1"]

    ext_addrs = ["1Lqf8UgzG3SWWTe9ab8YPwgm6gzkJCZMX6",
                 "1KuwentNouJBjKZgfrcPidSBELyXkpvpDa",
                 "1DgSD3feEKysnre6bL2xQAUyza4cdShVX1",
                 "1JefJedKMWX4NowgGujdhr7Lq3EFHtwDjQ",
                 "1A994BxdSc5HzNeQ8vUUrZJ7X1azjvkQ9"]

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
    assert wallet.balances == (100000, 20000)
    
    # Check that we can get a new payout address
    for i in range(3):
        ext_addr = wallet.get_new_payout_address("default")
        assert ext_addr == ext_addrs[i + 1]
        assert wallet.accounts[0].last_indices[0] == i + 1
        assert wallet.accounts[0].current_payout_address == ext_addr

    # Check the balance again - should be the same
    assert wallet.balances == (100000, 20000)

    # Check it after updating the mock
    m.set_num_used_addresses(0, 4, 0)
    assert wallet.balances == (400000, 20000)
        
    
