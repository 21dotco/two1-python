from functools import update_wrapper

# constants (in satoshi)
BLOCKCHAIN_TX_FEE_MIN = 1000
BLOCKCHAIN_TX_FEE_MAX = 10000

def verify_balances(balance_delta=0, onchain_delta=0, onchain_transactions=0):
    """Runs a test and verifies that balances get modified appropriately.
       An appropriate transaction fee range is added to blockchain_delta
       for each blockchain transaction.
    """

    def _verify_balances(f):
      def wrapper(cli_runner, *args, **kwargs):
          prev_wallet = cli_runner.get_status()["wallet"]["wallet"]
          prev_balance = int(prev_wallet["twentyone_balance"])
          prev_onchain = int(prev_wallet["onchain"])

          result = f(cli_runner, *args, **kwargs)

          cur_wallet = cli_runner.get_status()["wallet"]["wallet"]
          cur_balance = int(cur_wallet["twentyone_balance"])
          cur_onchain = int(cur_wallet["onchain"])

          # verify balance

          if prev_balance + balance_delta < 0:
              # not enough money
              assert cur_balance == prev_balance
          else:
              assert cur_balance == prev_balance + balance_delta

          if onchain_delta == 0 and onchain_transactions == 0:
              # no onchain transactions
              assert cur_onchain == prev_onchain
          else:
              tx_fee_min = BLOCKCHAIN_TX_FEE_MIN * onchain_transactions
              tx_fee_max = BLOCKCHAIN_TX_FEE_MAX * onchain_transactions

              # boolean values for assertions
              onchain_unchanged = (cur_onchain == prev_onchain)
              onchain_changed_min = (cur_onchain >= prev_onchain + onchain_delta - tx_fee_max)
              onchain_changed_max = (cur_onchain <= prev_onchain + onchain_delta - tx_fee_min)

              if prev_onchain + onchain_delta < tx_fee_min:
                  # not enough money
                  assert onchain_unchanged
              elif prev_onchain + onchain_delta >= tx_fee_min and prev_onchain + onchain_delta <= tx_fee_max:
                  # check special case - if onchain balance is in range [cost + min_tx, cost + max_tx]
                  # this could either go through or not
                  assert onchain_unchanged or (onchain_changed_min and onchain_changed_max)
              else:
                  # tx should go through
                  assert (onchain_changed_min and onchain_changed_max)

          return result

      return update_wrapper(wrapper, f)
    return _verify_balances