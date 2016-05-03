from two1.wallet.fees import get_fees


def _get_utxos_addr_tuple_list(utxos_by_addr):
    utxo_tuple_list = []
    for addr, utxos_addr in utxos_by_addr.items():
        for u in utxos_addr:
            utxo_tuple_list.append((addr, u))

    return utxo_tuple_list


def utxo_selector_smallest_first(utxos_by_addr, amount,
                                 num_outputs, fees=None):
    f = get_fees()
    input_fee = f['per_input']
    output_fee = f['per_output']

    # Order the utxos by amount
    utxo_tuple_list = _get_utxos_addr_tuple_list(utxos_by_addr)
    ordered_utxos = sorted(utxo_tuple_list,
                           key=lambda utxo_addr_tuple: utxo_addr_tuple[1].value)

    calc_fees = num_outputs * output_fee
    utxos_to_use = {}
    utxo_sum = 0

    for addr, utxo in ordered_utxos:
        tf = fees if fees is not None else calc_fees
        if utxo_sum < amount + tf:
            utxo_sum += utxo.value
            if addr in utxos_to_use:
                utxos_to_use[addr].append(utxo)
            else:
                utxos_to_use[addr] = [utxo]

            calc_fees += input_fee
        else:
            break

    fee = fees if fees is not None else calc_fees

    rv = utxos_to_use, fee
    if utxo_sum < amount + fee:
        rv = {}, fee

    return rv


def _fee_calc(num_utxos, total_value, fee_amounts):
    return num_utxos * fee_amounts['per_input'] + fee_amounts['per_output']
