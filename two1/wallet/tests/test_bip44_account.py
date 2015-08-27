import math
import pytest
from unittest.mock import MagicMock

from two1.bitcoin.crypto import HDKey, HDPrivateKey, HDPublicKey

from two1.wallet.bip44_account import BIP44Account
from two1.wallet.two1_wallet import Two1Wallet
from two1.wallet.mock_txn_data_provider import MockTransactionDataProvider

master_key_mnemonic = 'cage minimum apology region aspect wrist demise gravity another bulb tail invest'
master_key_passphrase = "test"

master_key = HDPrivateKey.master_key_from_mnemonic(mnemonic=master_key_mnemonic,
                                                   passphrase=master_key_passphrase)
acct0_key = HDKey.from_path(master_key, [Two1Wallet.PURPOSE_CONSTANT, Two1Wallet.BITCOIN_MAINNET, 0])

mock_txn_provider = MockTransactionDataProvider(acct0_key)

def test_init():
    with pytest.raises(TypeError):
        acct = BIP44Account(master_key_passphrase, "default", 0, mock_txn_provider)

    with pytest.raises(AssertionError):
        acct = BIP44Account(master_key, "default", 0, mock_txn_provider)

@pytest.mark.parametrize("num_used_payout_addresses, num_used_change_addresses, expected_balance",
                         [(0, 0, (0, 0)),
                          (1, 0, (100000, 0)),
                          (1, 2, (100000, 20000)),
                          (41, 2, (4100000, 20000)),
                          (41, 45, (4100000, 450000)),
                          (55, 60, (5500000, 600000))])
def test_all(num_used_payout_addresses, num_used_change_addresses, expected_balance):
    m = mock_txn_provider
    m.reset_mocks()
    m.num_used_payout_addresses = num_used_payout_addresses
    m.num_used_change_addresses = num_used_change_addresses    
    total_used = num_used_payout_addresses + num_used_change_addresses
    
    m.set_txn_side_effect_for_hd_discovery(False)
    expected_call_count = m.set_txn_side_effect_for_hd_discovery(True, True)

    acct = BIP44Account(acct0_key, "default", 0, m)

    assert acct._chain_priv_keys[0].to_b58check() == mock_txn_provider.payout_key.to_b58check()
    assert m.get_transactions.call_count == expected_call_count

    assert len(acct._used_addresses[0]) == num_used_payout_addresses
    assert len(acct._used_addresses[1]) == num_used_change_addresses
    assert acct.last_indices[0] == num_used_payout_addresses - 1
    assert acct.last_indices[1] == num_used_change_addresses - 1

    assert acct.balance == expected_balance

    if total_used:
        assert acct.has_txns()
    else:
        assert not acct.has_txns()

    exp_used = m.payout_addresses[:num_used_payout_addresses] + m.change_addresses[:num_used_change_addresses]
    assert acct.all_used_addresses == exp_used

    change_index = 0 if num_used_change_addresses == 0 else num_used_change_addresses - 1
    payout_index = 0 if num_used_payout_addresses == 0 else num_used_payout_addresses - 1
    assert acct.current_change_address == m.change_addresses[change_index]
    assert acct.current_payout_address == m.payout_addresses[payout_index]
