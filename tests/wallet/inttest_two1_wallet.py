import time

import random
from two1.blockchain.twentyone_provider import TwentyOneProvider
from two1.wallet.two1_wallet import Two1Wallet

mnemonics = ['absent paddle capable spell bag reflect rally there swear swallow cook rubber',
             'stairs art mirror spoon clap talk exclude tuna absurd exact grape relief',
             'poem into dune liar already rain swear thunder spread kangaroo monster wise',
             'business lyrics news image duty stone clerk salad harvest shallow follow evoke',
             'another student leg ladder jeans hello cluster type network wrist before sense']

cp = TwentyOneProvider()

# Create wallet objects
wallets = [Two1Wallet.import_from_mnemonic(data_provider=cp,
                                           mnemonic=m,
                                           account_type='BIP32')
           for m in mnemonics]

max_balance_index = -1
max_balance = 0
for i, w in enumerate(wallets):
    balance = w.balances

    if balance['confirmed'] > max_balance:
        max_balance = balance['confirmed']
        max_balance_index = i

    print("\nWallet %d:" % i)
    print("----------")
    print("Num accounts: %d" % (len(w._accounts)))
    print("Balance %d satoshis (confirmed), %d satoshis (total)" %
          (balance['confirmed'], balance['total']))
    for acct in w._accounts:
        print("Acct: %d, last_used_indices: %r" %
              (acct.index & 0x7fffffff, acct.last_indices))

    print("Next payout address: %s" % w.get_payout_address())

print()

# Now send random amounts to all the other wallets
max_amount = max_balance // (2 * len(wallets))
sending_wallet = wallets[max_balance_index]

expected_balances = {}
send_addresses_amounts = {}
total_to_send = 0
for i, w in enumerate(wallets):
    if i == max_balance_index:
        continue

    amount = random.randrange(max_amount)
    total_to_send += amount
    expected_balances[i] = w.confirmed_balance() + amount
    address = w.current_address
    send_addresses_amounts[address] = amount

    print("Sending %d satoshis to wallet %d, address %s." %
          (amount, i, address))

res = sending_wallet.send_to_multiple(send_addresses_amounts)
if res:
    print("Transaction successfully sent. TXIDs:")
    for r in res:
        print(r["txid"])

    # Wait until the balance in the sending wallet goes down
    print("\nWaiting up to 15 minutes for txn confirmation ...")
    start_time = time.time()
    while sending_wallet.confirmed_balance() >= max_balance - total_to_send:
        time.sleep(10)

        if time.time() - start_time > 900:
            print("Unsuccessfully waited 900s for balance update.")
            break

    # Check the balances against expectation
    for i, w in enumerate(wallets):
        if i == max_balance_index:
            continue

        balance = w.confirmed_balance()
        if balance != expected_balances[i]:
            print("Wallet %d balance (%d) does not match expected (%d)!!!" %
                  (i, balance, expected_balances[i]))

    # Print the update balance for the sending wallet
    print("Updated balances for sending wallet (index: %d): %r" %
          (max_balance_index, sending_wallet.balances))
