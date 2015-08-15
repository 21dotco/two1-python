import requests

# use pycoin for now. This will be replaced with our Bitcoin utils
from pycoin import tx
# import json


class BitcoinInterface(object):

    def __init__(self):
        self.auth = (
            'a96f8c3c18abe407757713a09614ba0b',
            'a13421f9347421e88c17d8388638e311')
        self.API_base = 'https://api.chain.com/v2/bitcoin/'

    def get_tx(self, txId):
        getBlock = self.API_base + 'transactions/' + txId
        r = requests.get(getBlock, dict(), auth=self.auth)
        # for k,v in r.json().items():
        #     print(k,v)
        return r.json()

    def check_txid(self, txId, address, amount):
        t = self.get_tx(txId)
        if "outputs" in t:
            for output in t["outputs"]:
                if "addresses" in output and "value" in output:
                    output_a = output["addresses"]
                    if len(output_a) == 1 and output_a[0] == address:
                        if output["value"] >= amount:
                            return True

        return False

    def check_tx(self, tx, address, amount):
        # check if parses as a transaction
        try:
            parsed_tx = tx.Tx.tx_from_hex(tx)
            for out in parsed_tx.txs_out:
                if out.bitcoin_address() == address:
                    if out.coin_value >= amount:
                        return True
        except:
            print("Tx parsing error")

        return False

    def check_payment (self, tx, address, amount):
        # if its a txId (hex format)
        if len(tx) == 64:  # this probably a txId
            return self.check_txid(tx, address, amount)
        else:
            return self.check_tx(tx, address, amount)
            # error parsing
