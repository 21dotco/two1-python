import pytest
from two1.bitcoin.crypto import HDPublicKey
from two1.blockchain.chain_provider import ChainProvider
from two1.wallet.exceptions import WalletBalanceError
from two1.wallet.utxo_selectors import utxo_selector_smallest_first


API_KEY = 'a96f8c3c18abe407757713a09614ba0b'
API_SECRET = 'a13421f9347421e88c17d8388638e311'

acct_pub_key = HDPublicKey.from_b58check("xpub68YdQASJ3w2RYS7XNT8HkLVjWqKeMD5uAxJR2vqXAh65j7izto1cVSwCNm7awAjjeYExqneCAZzt5xGETXZz1EXa9HntM5HzwdQ9551UErA")


def test_smallest_first():
    cp = ChainProvider(API_KEY, API_SECRET)

    utxos_by_addr = cp.get_utxos_hd(acct_pub_key, 10, 10)

    utxos = []
    for addr, addr_utxos in utxos_by_addr.items():
        utxos += addr_utxos

    amount = 1000000
    with pytest.raises(WalletBalanceError):
        selected, fees = utxo_selector_smallest_first(data_provider=cp,
                                                      utxos_by_addr=utxos_by_addr,
                                                      amount=amount,
                                                      num_outputs=2)

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
