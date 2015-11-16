import arrow
import json

from calendar import timegm

from collections import defaultdict
from two1.lib.blockchain import exceptions
from two1.lib.blockchain.base_provider import BaseProvider
from two1.lib.bitcoin.hash import Hash
from two1.lib.bitcoin.txn import UnspentTransactionOutput
from two1.lib.bitcoin.txn import TransactionInput
from two1.lib.bitcoin.txn import TransactionOutput
from two1.lib.bitcoin.txn import Transaction
from two1.lib.bitcoin.utils import bytes_to_str
from two1.lib.bitcoin.utils import pack_var_str
from two1.lib.bitcoin.script import Script


class ChainProvider(BaseProvider):
    """ Transaction data provider using the chain API

        Args:
            api_key_id (str): chain.com API key
            api_key_secret (str): chain.com API secret
            testnet (bool, optional): True for testnet, False for
            mainnet (default)
    """

    def __init__(self, api_key_id, api_key_secret, testnet=False,
                 connection_pool_size=0):
        super().__init__()
        self.testnet = testnet
        self.auth = (api_key_id, api_key_secret)
        self._set_url()
        self._session = None
        self._pool_size = connection_pool_size

    @property
    def testnet(self):
        return self._testnet

    @testnet.setter
    def testnet(self, v):
        self._testnet = bool(v)
        self.chain = "testnet3" if self._testnet else "bitcoin"
        self._set_url()

    def _set_url(self):
        self.server_url = 'https://api.chain.com/v2/' + self.chain + "/"

    def _create_session(self):
        import requests
        self._session = requests.Session()
        if self._pool_size > 0:
            adapter = requests.adapters.HTTPAdapter(pool_connections=self._pool_size,
                                                    pool_maxsize=self._pool_size)
            self._session.mount('http://', adapter)
            self._session.mount('https://', adapter)
        self._session.auth = self.auth

    @staticmethod
    def txn_from_json(txn_json):
        # {
        # "hash": "0bf0de38c26195919179f...",
        # "block_hash": "000000000000000...",
        # "block_height": 303404,
        # "block_time": "2014-05-30T23:54:55Z",
        # "chain_received_at": "2015-08-13T10:52:21.718Z",
        # "confirmations": 69389,
        # "lock_time": 0,
        # "inputs": [
        #   {
        #     "transaction_hash": "0bf0de38c2619...",
        #     "output_hash": "b84a66c46e24fe71f9...",
        #     "output_index": 0,
        #     "value": 300000,
        #     "addresses": [
        #       "3L7dKYQGNoZub928CJ8NC2WfrM8U8GGBjr"
        #     ],
        #     "script_signature": "03046022100de7b67b9...",
        #     "script_signature_hex": "00493046022100de7b...",
        #     "sequence": 4294967295
        #   }
        # ],
        # "outputs": [
        #   {
        #     "transaction_hash": "0bf0de38c261959...",
        #     "output_index": 0,
        #     "value": 290000,
        #     "addresses": [
        #       "1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb"
        #     ],
        #     "script": "OP_DUP OP_HASH160 c629680b8d...",
        #     "script_hex": "76a914c629680b8d13...",
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
        inputs = []
        outputs = []
        addr_keys = set()
        for i in txn_json["inputs"]:
            # Chain doesn't return the stuff about script length etc, so
            # we need to prepend that.
            script, _ = Script.from_bytes(
                pack_var_str(bytes.fromhex(i["script_signature_hex"])))
            inputs.append(TransactionInput(Hash(i["output_hash"]),
                                           i["output_index"],
                                           script,
                                           i["sequence"]))
            if "addresses" in i:
                addr_keys.add(i["addresses"][0])

        for i in txn_json["outputs"]:
            script, _ = Script.from_bytes(
                pack_var_str(bytes.fromhex(i["script_hex"])))
            outputs.append(TransactionOutput(i["value"],
                                             script))
            if "addresses" in i:
                addr_keys.add(i["addresses"][0])

        txn = Transaction(Transaction.DEFAULT_TRANSACTION_VERSION,
                          inputs,
                          outputs,
                          txn_json["lock_time"])

        return txn, addr_keys

    @staticmethod
    def _list_chunks(lst, chunk_size):
        for i in range(0, len(lst), chunk_size):
            yield lst[i:i + chunk_size]

    def _request(self, method, path, **kwargs):
        import requests
        if self._session is None:
            self._create_session()

        url = self.server_url + path
        result = None
        try:
            result = self._session.request(method,
                                           url,
                                           auth=self.auth,
                                           **kwargs)

            # A non 200 status_code from Chain API is an exception
            if result.status_code != 200:
                data = result.json()
                raise exceptions.DataProviderError(data['message'])
            return result

        except requests.exceptions.ConnectionError:
            raise exceptions.DataProviderUnavailableError("Could not connect to service.")
        except requests.exceptions.Timeout:
            raise exceptions.DataProviderUnavailableError("Connection timed out.")
        except ValueError:
            if result:
                raise exceptions.DataProviderError(result.text)
            else:
                raise
        except KeyError:
            if result:
                raise exceptions.DataProviderError(result.text)
            else:
                raise
        except Exception as e:
            raise exceptions.DataProviderError(e)

    def get_balance(self, address_list):
        """ Provides the balance for each address.

            The balance is computed by looking up the transactions associated
            with each address in address_list, summing all received coins and
            subtracting all coins payed out. It makes a distinction between
            confirmed and total transactions.

        Args:
            address_list (list(str)): List of Base58Check encoded
            Bitcoin addresses.

        Returns:
            dict: A dict keyed by address with each value being a dict
            containing the confirmed and total balances.
        """
        ret = {}
        for addresses in self._list_chunks(address_list, 25):
            r = self._request("GET", "addresses/" + ",".join(addresses))
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
                ret[d["address"]] = {"confirmed": d["confirmed"]["balance"],
                                     "total": d["total"]["balance"]}

        return ret

    def get_transactions(self, address_list, limit=100, min_block=None):
        """ Provides transactions associated with each address in address_list.

        Args:
            address_list (list(str)): List of Base58Check encoded Bitcoin
            addresses.
            limit (int): Maximum number of transactions to return.
            min_block (int): Block height from which to start getting
                transactions. If None, will get transactions from the
                entire blockchain.

        Returns:
            dict: A dict keyed by address with each value being a list of
            Transaction
               objects.
        """
        ret = defaultdict(list)
        for addresses in self._list_chunks(address_list, 199):
            r = self._request("GET", "addresses/" + ",".join(addresses)
                              + "/transactions?limit={}".format(limit))
            txn_data = r.json()

            for data in txn_data:
                block_hash = None
                if data['block_hash']:
                    block_hash = Hash(data['block_hash'])
                metadata = dict(block=data['block_height'],
                                block_hash=block_hash,
                                network_time=timegm(arrow.get(
                                    data['chain_received_at']).datetime.timetuple()),
                                confirmations=data['confirmations'])

                txn, addr_keys = self.txn_from_json(data)
                for addr in addr_keys:
                    if addr in addresses:
                        ret[addr].append(dict(metadata=metadata,
                                              transaction=txn))

        return ret

    def get_transactions_by_id(self, ids):
        """ Gets transactions by their IDs.

        Args:
            ids (list(str)): List of TXIDs to retrieve.

        Returns:
            dict: A dict keyed by TXID of Transaction objects.
        """
        ret = {}
        for txid in ids:
            r = self._request("GET", "transactions/%s" % txid)
            data = r.json()

            if r.status_code == 200:
                block_hash = None
                if data['block_hash']:
                    block_hash = Hash(data['block_hash'])
                metadata = dict(block=data['block_height'],
                                block_hash=block_hash,
                                network_time=timegm(arrow.get(
                                    data['chain_received_at']).datetime.timetuple()),
                                confirmations=data['confirmations'])
                txn, _ = self.txn_from_json(data)
                assert str(txn.hash) == txid

                ret[txid] = dict(metadata=metadata,
                                 transaction=txn)

        return ret

    def get_utxos(self, address_list):
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
            data = r.json()

            # for each address
            # {
            #     "transaction_hash": "0bf0de38c261...",
            #     "output_index": 0,
            #     "value": 290000,
            #     "addresses": [
            #         "1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb"
            #     ],
            #     "script": "OP_DUP OP_HASH160 c6296...",
            #     "script_hex": "76a914c629680b8d1...",
            #     "script_type": "pubkeyhash",
            #     "required_signatures": 1,
            #     "spent": false,
            #     "confirmations": 8758
            # },

            for d in data:
                address = d["addresses"][0]
                txn_hash = Hash(d["transaction_hash"])
                script, _ = Script.from_bytes(
                    pack_var_str(bytes.fromhex(d["script_hex"])))
                ret[address].append(UnspentTransactionOutput(txn_hash,
                                                             d["output_index"],
                                                             d["value"],
                                                             script,
                                                             d["confirmations"]))
        return ret

    def broadcast_transaction(self, transaction):
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
            raise TypeError(
                "transaction must be one of: bytes, str, Transaction.")

        data = {"signed_hex": signed_hex}
        r = self._request("POST", "transactions/send", json=data)
        if r.status_code == 200:
            j = r.json()
            return j["transaction_hash"]
        elif r.status_code == 400:
            j = r.json()

            # TODO: Change this to some more meaningful exception type
            raise exceptions.TransactionBroadcastError(j['message'])
        else:
            # Some other status code... should never happen.
            raise exceptions.TransactionBroadcastError(
                "Unexpected response: %r" % r.status_code)

    def get_block_height(self):
        """ Returns the latest block height

        Returns:
            int: Block height
        """
        r = self._request("GET", "blocks/latest")

        ret = None
        if r.status_code == 200:
            data = r.json()
            ret = data['height']

        return ret
