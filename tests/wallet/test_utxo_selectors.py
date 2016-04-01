import random

from two1.bitcoin.txn import UnspentTransactionOutput
from two1.bitcoin.hash import Hash
from two1.bitcoin.script import Script
from two1.wallet.utxo_selectors import utxo_selector_smallest_first


def test_smallest_first():
    utxos_by_addr = {}

    addr_base = "1LQ1TjCKJN8GXsYtsqnREqs5Z4eaPCu5p"
    h = Hash("a2972893f1be1f54d68a9228d9706ff8f202bb80f488f4dd46c0fe37c1e42415")
    for i in range(10):
        addr = addr_base + str(i)
        utxos_by_addr[addr] = [UnspentTransactionOutput(
            transaction_hash=h,
            outpoint_index=random.randint(0, 10),
            value=i*20000,
            scr=Script(""),
            confirmations=10)]

    utxos = []
    for addr, addr_utxos in utxos_by_addr.items():
        utxos += addr_utxos

    amount = 1000000
    selected, fees = utxo_selector_smallest_first(utxos_by_addr=utxos_by_addr,
                                                  amount=amount,
                                                  num_outputs=2)
    assert not selected

    amount = 100000
    selected, fees = utxo_selector_smallest_first(utxos_by_addr=utxos_by_addr,
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
