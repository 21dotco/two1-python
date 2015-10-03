import os
import pytest
from two1.lib.bitcoin.crypto import HDPublicKey
from two1.lib.blockchain.chain_provider import ChainProvider
from two1.lib.wallet.exceptions import WalletBalanceError
from two1.lib.wallet.utxo_selectors import utxo_selector_smallest_first


acct_pub_key = HDPublicKey.from_b58check("xpub68YdQASJ3w2RYS7XNT8HkLVjWqKeMD5uAxJR2vqXAh65j7izto1cVSwCNm7awAjjeYExqneCAZzt5xGETXZz1EXa9HntM5HzwdQ9551UErA")
API_KEY_ID = os.environ.get("CHAIN_API_KEY_ID", None)
API_KEY_SECRET = os.environ.get("CHAIN_API_KEY_SECRET", None)
chain_key_present = pytest.mark.skipif(API_KEY_ID is None or API_KEY_SECRET is None,
                                       reason="CHAIN_API_KEY_ID or CHAIN_API_KEY_SECRET\
                                       is not available in env")


@chain_key_present
def test_smallest_first():
    cp = ChainProvider(API_KEY_ID, API_KEY_SECRET)

    payout_key = HDPublicKey.from_parent(acct_pub_key, 0)
    change_key = HDPublicKey.from_parent(acct_pub_key, 1)

    addrs = [HDPublicKey.from_parent(payout_key, i).address(True) for i in range(10)]
    addrs += [HDPublicKey.from_parent(change_key, i).address(True) for i in range(10)]

    utxos_by_addr = cp.get_utxos(addrs)

    utxos = []
    for addr, addr_utxos in utxos_by_addr.items():
        utxos += addr_utxos

    amount = 1000000
    selected, fees = utxo_selector_smallest_first(data_provider=cp,
                                                  utxos_by_addr=utxos_by_addr,
                                                  amount=amount,
                                                  num_outputs=2)
    assert not selected

    amount = 100000
    selected, fees = utxo_selector_smallest_first(data_provider=cp,
                                                  utxos_by_addr=utxos_by_addr,
                                                  amount=amount,
                                                  num_outputs=2)

    sum_selected = 0
    remaining = []
    selected_list = []
    for addr, utxo_list in selected.items():
        sum_selected += sum([utxo.value for utxo in utxo_list])
        selected_list += utxo_list

    assert sum_selected >= amount

    remaining = [u for u in utxos if u not in selected_list]

    largest_selected = 0
    for s in selected_list:
        if s.value > largest_selected:
            largest_selected = s.value

    # Make sure that the largest of the selected is <= min(remaining)
    assert largest_selected <= min([u.value for u in remaining])
