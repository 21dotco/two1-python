"""This submodule provides a concrete `InsightProvider` class that provides
information about a blockchain by contacting a server."""
import decimal

from urllib.parse import urljoin

from collections import defaultdict
from two1.blockchain import exceptions
from two1.blockchain.base_provider import BaseProvider
from two1.bitcoin.txn import CoinbaseInput
from two1.bitcoin.txn import TransactionInput
from two1.bitcoin.txn import TransactionOutput
from two1.bitcoin.txn import Transaction
from two1.bitcoin.utils import bytes_to_str
from two1.bitcoin.hash import Hash
from two1.bitcoin.script import Script


class InsightProvider(BaseProvider):
    """ Transaction data provider using the insight API

        Args:
            insight_host_name (str): Host name (with port).
            insight_api_path (str): Usually either "api" or "insight-api".
            testnet (bool, optional): True for testnet, False for
            mainnet (default)
            connection_pool_size (int): Number of connections to pool.
    """
    DEFAULT_HOST = "https://insight.bitpay.com"

    def __init__(self, insight_host_name=DEFAULT_HOST, insight_api_path="api",
                 testnet=False,
                 connection_pool_size=0):
        if insight_host_name is None:
            insight_host_name = self.DEFAULT_HOST
        if insight_api_path is None:
            insight_api_path = "api"
        self.host_name = insight_host_name
        self.api_path = insight_api_path
        self.testnet = testnet
        self.auth = None
        self._session = None
        self._pool_size = connection_pool_size
        self.can_limit_by_height = True

    @property
    def testnet(self):
        """ Returns whether or not the data provider is on testnet."""
        return self._testnet

    @testnet.setter
    def testnet(self, v):
        self._testnet = bool(v)
        self.chain = "testnet3" if self._testnet else "bitcoin"
        self._set_url()

    def _set_url(self):
        self.server_url = urljoin(self.host_name, self.api_path) + "/"

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
        """ Returns a new Transaction from a JSON-serialized transaction

        Args:
            txn_json: JSON with the following format:

        {
        "hash": "0bf0de38c26195919179f...",
        "block_hash": "000000000000000...",
        "block_height": 303404,
        "block_time": "2014-05-30T23:54:55Z",
        "chain_received_at": "2015-08-13T10:52:21.718Z",
        "confirmations": 69389,
        "lock_time": 0,
        "inputs": [
          {
            "transaction_hash": "0bf0de38c2619...",
            "output_hash": "b84a66c46e24fe71f9...",
            "output_index": 0,
            "value": 300000,
            "addresses": [
              "3L7dKYQGNoZub928CJ8NC2WfrM8U8GGBjr"
            ],
            "script_signature": "03046022100de7b67b9...",
            "script_signature_hex": "00493046022100de7b...",
            "sequence": 4294967295
          }
        ],
        "outputs": [
          {
            "transaction_hash": "0bf0de38c261959...",
            "output_index": 0,
            "value": 290000,
            "addresses": [
              "1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb"
            ],
            "script": "OP_DUP OP_HASH160 c629680b8d...",
            "script_hex": "76a914c629680b8d13...",
            "script_type": "pubkeyhash",
            "required_signatures": 1,
            "spent": false,
            "spending_transaction": null
          }
        ],
        "fees": 10000,
        "amount": 290000
        },
        Transaction.DEFAULT_TRANSACTION_VERSION

        Returns:
            two1.bitcoin.Transaction: a deserialized transaction derived
                from the provided json.

        """
        inputs = []
        outputs = []
        addr_keys = set()

        for i in sorted(txn_json["vin"], key=lambda i: i["n"]):
            if 'coinbase' in i:
                inputs.append(CoinbaseInput(height=0,
                                            raw_script=bytes.fromhex(i['coinbase']),
                                            sequence=i['sequence'],
                                            block_version=1))
            else:
                script = Script.from_hex(i["scriptSig"]["hex"])
                inputs.append(TransactionInput(Hash(i["txid"]),
                                               i["vout"],
                                               script,
                                               i["sequence"]))
            if "addr" in i:
                addr_keys.add(i["addr"])

        for o in sorted(txn_json["vout"], key=lambda o: o["n"]):
            script = Script.from_hex(o["scriptPubKey"]["hex"])
            value = int(decimal.Decimal(str(o["value"])) * decimal.Decimal('1e8'))
            outputs.append(TransactionOutput(value, script))

            if "addresses" in o["scriptPubKey"]:
                for a in o["scriptPubKey"]["addresses"]:
                    addr_keys.add(a)

        txn = Transaction(Transaction.DEFAULT_TRANSACTION_VERSION,
                          inputs,
                          outputs,
                          txn_json["locktime"])

        assert txn.hash == Hash(txn_json['txid'])

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
        headers = {"Content-Type": "application/json; charset=utf-8"}
        try:
            result = self._session.request(method,
                                           url,
                                           headers=headers,
                                           auth=self.auth,
                                           **kwargs)

            # A non 200 status_code from Insight API is an exception
            if result.status_code == 503:
                raise exceptions.DataProviderError(result.text)
            if result.status_code != 200:
                try:
                    data = result.json()
                    msg = data['message']
                except:
                    msg = result.text
                raise exceptions.DataProviderError(msg)
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
            Transaction objects.
        """
        last_block_index = self.get_block_height()
        ret = defaultdict(list)
        total_items = limit
        for addresses in self._list_chunks(address_list, 199):
            fr = 0
            to = min(100, limit)

            while fr < total_items:
                req = "addrs/" + ",".join(addresses) + \
                      "/txs?from=%d&to=%d" % (fr, to)

                r = self._request("GET", req)
                txn_data = r.json()

                if "totalItems" in txn_data:
                    total_items = txn_data["totalItems"]

                fr = txn_data["to"]
                to = fr + 100

                for data in txn_data['items']:
                    if "vin" not in data or "vout" not in data:
                        continue
                    block_hash = None
                    block = None
                    if data['confirmations'] > 0:
                        block = last_block_index - data['confirmations'] + 1
                        block_hash = Hash(data['blockhash'])

                    metadata = dict(block=block,
                                    block_hash=block_hash,
                                    network_time=data.get("time", None),
                                    confirmations=data['confirmations'])

                    if min_block and block:
                        if block < min_block:
                            continue

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
        last_block_index = self.get_block_height()
        ret = {}
        for txid in ids:
            r = self._request("GET", "tx/%s" % txid)
            data = r.json()

            if r.status_code == 200:
                if "vin" not in data or "vout" not in data:
                    continue
                block_hash = None
                block = None
                if data['confirmations'] > 0:
                    block = last_block_index - data['confirmations'] + 1
                    block_hash = Hash(data['blockhash'])

                metadata = dict(block=block,
                                block_hash=block_hash,
                                network_time=data['time'],
                                confirmations=data['confirmations'])

                txn, _ = self.txn_from_json(data)
                assert str(txn.hash) == txid

                ret[txid] = dict(metadata=metadata,
                                 transaction=txn)

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

        data = {"rawtx": signed_hex}
        r = self._request("POST", "tx/send", json=data)

        if r.status_code == 200:
            j = r.json()
            return j["txid"]
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
        r = self._request("GET", "status")

        ret = None
        if r.status_code == 200:
            data = r.json()
            ret = data['info']['blocks']

        return ret
