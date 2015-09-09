import json
import requests
from collections import defaultdict
from two1.wallet.txn_data_provider import TransactionDataProvider
from two1.wallet.txn_data_provider import DataProviderUnAvailable
from two1.bitcoin.crypto import HDPublicKey
from two1.bitcoin.txn import UnspentTransactionOutput
from two1.bitcoin.txn import TransactionInput
from two1.bitcoin.txn import TransactionOutput
from two1.bitcoin.txn import Transaction
from two1.bitcoin.utils import bytes_to_str
from two1.bitcoin.utils import pack_var_str
from two1.bitcoin.hash import Hash
from two1.bitcoin.script import Script


class ChainTransactionDataProvider(TransactionDataProvider):

    """ Transaction data provider using the 21 server

        Args:
            api_key (str): chain.com API key
            api_secret (str): chain.com API secret
            chain (str, optional): 'bitcoin' for mainnet (default).
            'testnet3' for testnet
    """

    def __init__(self, api_key, api_secret, chain="bitcoin"):
        self.auth = (api_key, api_secret)
        self.server_url = 'https://api.chain.com/v2/' + chain + "/"

    @staticmethod
    def _list_chunks(lst, chunk_size):
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]

    def _request(self, method, path, **kwargs):
        url = self.server_url + path + "/"
        try:
            result = requests.request(method,
                                      url,
                                      auth=self.auth,
                                      **kwargs)

            return result
        except requests.exceptions.ConnectionError:
            raise DataProviderUnAvailable("Could not connect to service.")
        except requests.expcetions.Timeout:
            raise DataProviderUnAvailable("Connection timed out.")

    def _gen_hd_addresses(self, pub_key, last_payout_index, last_change_index):
        if not isinstance(pub_key, HDPublicKey):
            raise TypeError("pub_key must be an HDPublicKey object.")

        payout_chain_key = HDPublicKey.from_parent(pub_key, 0)
        change_chain_key = HDPublicKey.from_parent(pub_key, 1)

        address_list = []
        for i in range(max(last_payout_index, last_change_index) + 1):
            if i <= last_payout_index:
                address_list.append(HDPublicKey.from_parent(payout_chain_key, i).address())
            if i <= last_change_index:
                address_list.append(HDPublicKey.from_parent(change_chain_key, i).address())

        return address_list

    def get_balance(self, address_list):
        """ Provides the balance for each address.

            The balance is computed by looking up the transactions associated
            with each address in address_list, summing all received coins and
            subtracting all coins payed out. It makes a distinction between
            confirmed and unconfirmed transactions.

        Args:
            address_list (list(str)): List of Base58Check encoded
            Bitcoin addresses.

        Returns:
            dict: A dict keyed by address with each value being a tuple
            containing the confirmed and unconfirmed balances.
        """
        ret = {}
        for addresses in self._list_chunks(address_list, 199):
            r = self._request("GET", "addresses/" + ",".join(addresses))
            if r.status_code == 200:
                data = r.json()

                # for each address

                # {
                #     "address": "17x23dNjXJLzGMev6R63uyRhMWP1VHawKc",
                #     "total": {
                #       "balance": 5000000000,
                #       "received": 5000000000,
                #       "sent": 0
                #     },
                #     "confirmed": {
                #       "balance": 5000000000,
                #       "received": 5000000000,
                #       "sent": 0
                #     }
                # }

                for d in data:
                    ret[d["address"]] = (d["confirmed"]["balance"],
                                         d["total"]["balance"] -
                                         d["confirmed"]["balance"])
            elif r.status_code == 400:
                raise ValueError("Invalid bitcoin addresse/addresses.")
        return ret

    def get_transactions(self, address_list, limit=100):
        """ Provides transactions associated with each address in address_list.

        Args:
            address_list (list(str)): List of Base58Check encoded Bitcoin addresses.
            limit (int): Maximum number of transactions to return.

        Returns:
            dict: A dict keyed by address with each value being a list of Transaction
               objects.
        """
        ret = defaultdict(list)
        for addresses in self._list_chunks(address_list, 199):
            r = self._request("GET", "addresses/" + ",".join(addresses)
                              + "/transactions?limit={}".format(limit))
            if r.status_code == 200:
                txn_data = r.json()

                # {
                # "hash": "0bf0de38c26195919179f42d475beb7a6b15258c38b57236afdd60a07eddd2cc",
                # "block_hash": "00000000000000001ea5471a4edc67380f114c6cad06bfd59ac6508f90e8b252",
                # "block_height": 303404,
                # "block_time": "2014-05-30T23:54:55Z",
                # "chain_received_at": "2015-08-13T10:52:21.718Z",
                # "confirmations": 69389,
                # "lock_time": 0,
                # "inputs": [
                #   {
                #     "transaction_hash": "0bf0de38c26195919179f42d475beb7a6b15258c38b57236afdd60a07eddd2cc",
                #     "output_hash": "b84a66c46e24fe71f9d8ab29b06df932d77bec2cc0691799fae398a8dc9069bf",
                #     "output_index": 0,
                #     "value": 300000,
                #     "addresses": [
                #       "3L7dKYQGNoZub928CJ8NC2WfrM8U8GGBjr"
                #     ],
                #     "script_signature": "0 3046022100de7b67b96a6855fbc81c1a4b45d98ba6fef27ddda8739c5a3e7c70039685f7db0221008972607445195847631d902f594db6d712c315e0d49a2bee98125af8e1fefb5701 304402200cc13d8859247bff4ab4bc70964955fa4dbcd1a0dff0a84896be7d9a7757516202206e2c6c0aec6527ccf30305ad6e242c973aad011e9ccc18a0b75fd7be6c9b675301 5221032071a66eaed3dbe31a982dc337108b28bcffbf88d8cac8975194e184abdb36662102134541ec8f3dc2d382646bad199526a64080a66d27d2e156906bdb822774283921020431faa475c966c752e6cf97dfbb2c68c98b0013ca5c76b860263438850c2ba053ae",
                #     "script_signature_hex": "00493046022100de7b67b96a6855fbc81c1a4b45d98ba6fef27ddda8739c5a3e7c70039685f7db0221008972607445195847631d902f594db6d712c315e0d49a2bee98125af8e1fefb570147304402200cc13d8859247bff4ab4bc70964955fa4dbcd1a0dff0a84896be7d9a7757516202206e2c6c0aec6527ccf30305ad6e242c973aad011e9ccc18a0b75fd7be6c9b6753014c695221032071a66eaed3dbe31a982dc337108b28bcffbf88d8cac8975194e184abdb36662102134541ec8f3dc2d382646bad199526a64080a66d27d2e156906bdb822774283921020431faa475c966c752e6cf97dfbb2c68c98b0013ca5c76b860263438850c2ba053ae",
                #     "sequence": 4294967295
                #   }
                # ],
                # "outputs": [
                #   {
                #     "transaction_hash": "0bf0de38c26195919179f42d475beb7a6b15258c38b57236afdd60a07eddd2cc",
                #     "output_index": 0,
                #     "value": 290000,
                #     "addresses": [
                #       "1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb"
                #     ],
                #     "script": "OP_DUP OP_HASH160 c629680b8d13ca7a4b7d196360186d05658da6db OP_EQUALVERIFY OP_CHECKSIG",
                #     "script_hex": "76a914c629680b8d13ca7a4b7d196360186d05658da6db88ac",
                #     "script_type": "pubkeyhash",
                #     "required_signatures": 1,
                #     "spent": false,
                #     "spending_transaction": null
                #   }
                # ],
                # "fees": 10000,
                # "amount": 290000
                # },
                # Transaction.DEFAULT_TRANSACTION_VERSION
                for data in txn_data:
                    inputs = []
                    outputs = []
                    addr_keys = set()
                    for i in data["inputs"]:
                        # Chain doesn't return the stuff about script length etc, so
                        # we need to prepend that.
                        script, _ = Script.from_bytes(pack_var_str(bytes.fromhex(i["script_signature_hex"])))
                        inputs.append(TransactionInput(Hash(i["output_hash"]),
                                                       i["output_index"],
                                                       script,
                                                       i["sequence"]))
                        addr_keys.add(i["addresses"][0])

                    for i in data["outputs"]:
                        script, _ = Script.from_bytes(pack_var_str(bytes.fromhex(i["script_hex"])))
                        outputs.append(TransactionOutput(i["value"],
                                                         script))
                        addr_keys.add(i["addresses"][0])

                    for addr in addr_keys:
                        if addr in addresses:
                            ret[addr].append(Transaction(Transaction.DEFAULT_TRANSACTION_VERSION,
                                                         inputs,
                                                         outputs,
                                                         data["lock_time"]))
            elif r.status_code == 400:
                raise ValueError("Invalid bitcoin address/addresses.")
        return ret

    def get_utxo(self, address_list):
        """ Provides all unspent transactions associated with each address in
            the address_list.

        Args:
            address_list (list(str)): List of Base58Check encoded Bitcoin
            addresses.

        Returns:
            dict: A dict keyed by address with each value being a list of
               UnspentTransactionOutput objects.
        """
        ret = defaultdict(list)
        for addresses in self._list_chunks(address_list, 199):
            r = self._request("GET", "addresses/" + ",".join(addresses)
                              + "/unspents")
            if r.status_code == 200:
                data = r.json()

                # for each address
                # {
                #     "transaction_hash": "0bf0de38c26195919179f42d475beb7a6b15258c38b57236afdd60a07eddd2cc",
                #     "output_index": 0,
                #     "value": 290000,
                #     "addresses": [
                #         "1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb"
                #     ],
                #     "script": "OP_DUP OP_HASH160 c629680b8d13ca7a4b7d196360186d05658da6db OP_EQUALVERIFY OP_CHECKSIG",
                #     "script_hex": "76a914c629680b8d13ca7a4b7d196360186d05658da6db88ac",
                #     "script_type": "pubkeyhash",
                #     "required_signatures": 1,
                #     "spent": false,
                #     "confirmations": 8758
                # },

                for d in data:
                    address = d["addresses"][0]
                    txn_hash = Hash(d["transaction_hash"])
                    script = Script(d["script"])
                    ret[address].append(UnspentTransactionOutput(txn_hash,
                                                                 d["output_index"],
                                                                 d["value"],
                                                                 script,
                                                                 d["confirmations"]))
            elif r.status_code == 400:
                raise ValueError("Invalid bitcoin addresse/addresses.")
            return ret

    def get_balance_hd(self, pub_key, last_payout_index, last_change_index):
        """ Provides the balance for each address.

            Like TransactionDataProvider.get_balance() except that it uses the HD
            public key and returns balances for each payout address up to
            last_payout_index and each change address up to last_change_index.

        Args:
            pub_key (HDPublicKey): an extended public key from which change and
               payout addresses are derived.
            last_payout_index (int): Index of last payout address to return data for.
            last_change_index (int): Index of last change address to return data for.

        Returns:
            dict: A dict keyed by address with each value being a tuple containing
               the confirmed and unconfirmed balances.
        """
        return self.get_balance(self._gen_hd_addresses(pub_key, last_payout_index, last_change_index))

    def get_transactions_hd(self, pub_key, last_payout_index, last_change_index):
        """ Provides transactions associated with each address.

            Like TransactionDataProvider.get_transactions() except that it uses the HD
            public key and returns balances for each payout address up to
            last_payout_index and each change address up to last_change_index.

        Args:
            pub_key (HDPublicKey): an extended public key from which change and
               payout addresses are derived.
            last_payout_index (int): Index of last payout address to return data for.
            last_change_index (int): Index of last change address to return data for.

        Returns:
            dict: A dict keyed by address with each value being a list of Transaction
               objects.
        """
        return self.get_transactions(self._gen_hd_addresses(pub_key, last_payout_index, last_change_index))

    def get_utxo_hd(self, pub_key, last_payout_index, last_change_index):
        """ Provides all unspent transactions associated with each address.

            Like TransactionDataProvider.get_utxo() except that it uses the HD
            public key and returns balances for each payout address up to
            last_payout_index and each change address up to last_change_index.

        Args:
            pub_key (HDPublicKey): an extended public key from which change and
               payout addresses are derived.
            last_payout_index (int): Index of last payout address to return data for.
            last_change_index (int): Index of last change address to return data for.

        Returns:
            dict: A dict keyed by address with each value being a list of 
               UnspentTransactionOutput objects.
        """
        return self.get_utxo(self._gen_hd_addresses(pub_key, last_payout_index, last_change_index))
        
    def send_transaction(self, transaction):
        """ Broadcasts a transaction to the Bitcoin network
        
        Args:
            transaction (bytes or str): serialized, signed transaction

        Returns:
            str: The transaction ID
        """
        if isinstance(transaction, bytes):
            signed_hex = bytes_to_str(transaction)
        elif isinstance(transaction, Transaction):
            signed_hex = bytes_to_str(bytes(transaction))
        elif isinstance(transaction, str):
            signed_hex = transaction
        else:
            raise TypeError("transaction must be one of: bytes, str, Transaction.")
        
        data = {"signed_hex": signed_hex}
        r = self._request("POST", "transactions/send", data=data)

        if r.status_code == 200:
            j = r.json()
            return j["transaction_hash"]
        elif r.status_code == 400:
            j = r.json()
            
            # TODO: Change this to some more meaningful exception type
            raise ValueError(j['message'])
        else:
            # Some other status code... should never happen.
            raise ValueError("Unexpected response: %r" % r.status_code)
            
