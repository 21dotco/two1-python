import pytest

from two1.lib.bitcoin.crypto import HDKey, HDPrivateKey
from two1.lib.blockchain.mock_provider import MockProvider
from two1.lib.wallet.account_types import account_types
from two1.lib.wallet.hd_account import HDAccount


master_key_mnemonic = 'cage minimum apology region aspect wrist demise gravity another bulb tail invest'
master_key_passphrase = "test"

account_type = account_types['BIP44BitcoinMainnet']

master_key = HDPrivateKey.master_key_from_mnemonic(mnemonic=master_key_mnemonic,
                                                   passphrase=master_key_passphrase)
acct0_key = HDKey.from_path(master_key, account_type.account_derivation_prefix + "/0'")[-1]

mock_provider = MockProvider(account_type, master_key)


def test_init():
    with pytest.raises(TypeError):
        HDAccount(master_key_passphrase, "default", 0, mock_provider)

@pytest.mark.parametrize("num_used_payout_addresses, num_used_change_addresses, expected_balance",
                         [(0, 0, {'confirmed': 0, 'total': 0}),
                          (1, 0, {'confirmed': 100000, 'total': 100000}),
                          (1, 2, {'confirmed': 100000, 'total': 120000}),
                          (41, 2, {'confirmed': 4100000, 'total': 4120000}),
                          (41, 45, {'confirmed': 4100000, 'total': 4550000}),
                          (55, 60, {'confirmed': 5500000, 'total': 6100000})])
def test_all(num_used_payout_addresses, num_used_change_addresses, expected_balance):
    m = mock_provider
    m.reset_mocks()
    m.set_num_used_addresses(0, num_used_payout_addresses, 0)
    m.set_num_used_addresses(0, num_used_change_addresses, 1)
    m.set_num_used_accounts(1)
    total_used = num_used_payout_addresses + num_used_change_addresses

    expected_call_count = m.set_txn_side_effect_for_hd_discovery()

    acct = HDAccount(acct0_key, "default", 0, m)
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
    assert acct.current_change_address == mk0['change_addresses'][change_index]
    assert acct.current_payout_address == mk0['payout_addresses'][payout_index]
