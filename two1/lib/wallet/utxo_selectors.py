
from two1.lib.wallet.exceptions import WalletBalanceError

FEE_PER_KB = 10000  # Satoshis

# Each txn input is ~150 bytes:
# outpoint: 32 bytes
# outpoint index: 4 bytes
# signature: 77-78 bytes
# compressed public key: 33 bytes
# sequence num: 4 bytes
DEFAULT_INPUT_FEE = int(0.15 * FEE_PER_KB)

# Each txn output is ~40 bytes, thus 0.04
DEFAULT_OUTPUT_FEE = int(0.04 * FEE_PER_KB)


def _get_utxos_addr_tuple_list(utxos_by_addr):
    utxo_tuple_list = []
    for addr, utxos_addr in utxos_by_addr.items():
        for u in utxos_addr:
            utxo_tuple_list.append((addr, u))

    return utxo_tuple_list


def utxo_selector_smallest_first(data_provider, utxos_by_addr, amount,
                                 num_outputs, fees=None):
    # Order the utxos by amount
    utxo_tuple_list = _get_utxos_addr_tuple_list(utxos_by_addr)
    ordered_utxos = sorted(utxo_tuple_list,
                           key=lambda utxo_addr_tuple: utxo_addr_tuple[1].value)

    calc_fees = num_outputs * DEFAULT_OUTPUT_FEE
    utxos_to_use = {}
    utxo_sum = 0

    for addr, utxo in ordered_utxos:
        tf = fees if fees is not None else calc_fees + DEFAULT_INPUT_FEE
        if utxo_sum < amount + tf:
            utxo_sum += utxo.value
            if addr in utxos_to_use:
                utxos_to_use[addr].append(utxo)
            else:
                utxos_to_use[addr] = [utxo]

            calc_fees += DEFAULT_INPUT_FEE
        else:
            break

    f = fees if fees is not None else calc_fees

    rv = utxos_to_use, f
    if utxo_sum < amount + f:
        rv = {}, f

    return rv
