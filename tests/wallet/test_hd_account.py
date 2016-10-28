import pytest

from two1.bitcoin.crypto import HDKey, HDPrivateKey
from two1.blockchain.mock_provider import MockProvider
from two1.wallet.account_types import account_types
from two1.wallet.cache_manager import CacheManager
from two1.wallet.hd_account import HDAccount


master_key_mnemonic = 'cage minimum apology region aspect wrist demise gravity another bulb tail invest'
master_key_passphrase = "test"

account_type = account_types['BIP44BitcoinMainnet']

master_key = HDPrivateKey.master_key_from_mnemonic(mnemonic=master_key_mnemonic,
                                                   passphrase=master_key_passphrase)
acct0_key = HDKey.from_path(master_key, account_type.account_derivation_prefix + "/0'")[-1]

mock_provider = MockProvider(account_type, master_key)


def test_init():
    with pytest.raises(TypeError):
        HDAccount(master_key_passphrase, "default", 0, mock_provider,
                  CacheManager())


'''
The MockProvider is designed in a strange way that explains how the parameters
are chosen for test_all: the get_transactions side effects are set so that for
each DISCOVERY_INCREMENT block of addresses, a single transaction is returned
worth a fixed amount of satoshis (10k).
'''
increment = HDAccount.DISCOVERY_INCREMENT


@pytest.mark.parametrize("num_used_payout_addresses, num_used_change_addresses, expected_balance",
                         [(0, 0, {'confirmed': 0, 'total': 0}),
                          (1, 0, {'confirmed': 0, 'total': 100000}),
                          (1, 2, {'confirmed': 100000, 'total': 200000}),
                          (2*increment + 1, 2, {'confirmed': 100000, 'total': 400000}),
                          (2*increment + 1, increment + 1, {'confirmed': 200000, 'total': 500000}),
                          (2*increment + increment//2, 3 * increment, {'confirmed': 300000, 'total': 600000})])
def test_all(num_used_payout_addresses, num_used_change_addresses, expected_balance):
    m = mock_provider
    m.reset_mocks()
    m.set_num_used_addresses(0, num_used_payout_addresses, 0)
    m.set_num_used_addresses(0, num_used_change_addresses, 1)
    m.set_num_used_accounts(1)
    total_used = num_used_payout_addresses + num_used_change_addresses

    expected_call_count = m.set_txn_side_effect_for_hd_discovery()

    cm = CacheManager()
    acct = HDAccount(acct0_key, "default", 0, m, cm)
    mk0 = m._acct_keys[0]

    assert acct._chain_priv_keys[0].to_b58check() == mk0['payout_key'].to_b58check()
    assert m.get_transactions.call_count == expected_call_count

    assert acct.last_indices[0] == num_used_payout_addresses - 1
    assert acct.last_indices[1] == num_used_change_addresses - 1

    assert acct.balance == expected_balance

    if total_used:
        assert acct.has_txns()
    else:
        assert not acct.has_txns()

    exp_used = mk0['payout_addresses'][:num_used_payout_addresses] + \
        mk0['change_addresses'][:num_used_change_addresses]
    assert acct.all_used_addresses == exp_used

    change_index = 0 if num_used_change_addresses == 0 else num_used_change_addresses - 1
    payout_index = 0 if num_used_payout_addresses == 0 else num_used_payout_addresses - 1

    # The mock provider doesn't have a transaction per used address
    # so we need to check to see what the right index is
    change_addr = acct.get_address(True, change_index)
    payout_addr = acct.get_address(False, payout_index)

    if acct._cache_manager.address_has_txns(change_addr):
        change_index += 1

    if acct._cache_manager.address_has_txns(payout_addr):
        payout_index += 1

    assert acct.get_next_address(True) == mk0['change_addresses'][change_index]
    assert acct.get_next_address(False) == mk0['payout_addresses'][payout_index]
