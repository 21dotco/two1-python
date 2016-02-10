"""This submodule provides a concrete `BlockCypherProvider` class that provides
information about a blockchain by contacting a server."""
import arrow
import json
import time
from calendar import timegm

from collections import defaultdict
from collections import deque
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


class BlockCypherProvider(BaseProvider):
    """ Transaction data provider using the Blockcypher API

        Args:
            api_token (str): API token
            rate_limit_per_sec (int): API call peak rate limit / sec
            testnet (bool, optional): True for testnet, False for
            mainnet (default)
    """

    def __init__(self,
                 api_token="",
                 rate_limit_per_sec=3,
                 testnet=False,
                 connection_pool_size=0):
        super().__init__()
        self.testnet = testnet
        self.rate_limit_per_sec = rate_limit_per_sec
        self.api_token = api_token
        self._set_url()
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
        self._set_url()

    def _set_url(self):
        if self.testnet:
            chain = "test3"
        else:
            chain = "main"
        self.server_url = 'https://api.blockcypher.com/v1/btc/{}'.format(chain)

    def _create_session(self):
        import requests
        self._session = requests.Session()
        if self._pool_size > 0:
            adapter = requests.adapters.HTTPAdapter(pool_connections=self._pool_size,
                                                    pool_maxsize=self._pool_size)
            self._session.mount('http://', adapter)
            self._session.mount('https://', adapter)

    @staticmethod
    def txn_from_json(txn_json):
        """ Returns a new Transaction from a JSON-serialized transaction.

        Args:
            txn_json: JSON with the following format:

        {
        "block_hash": "0000000000000000af64802c79...",
        "block_height": 292586,
        "hash": "b4735a0690dab16b8789fceaf81c511f...",
        "addresses": [
            "18KXZzuC3xvz6upUMQpsZzXrBwNPWZjdSa",
            "1AAuRETEcHDqL4VM3R97aZHP8DSUHxpkFV",
            "1DEP8i3QJCsomS4BSMY2RpU1upv62aGvhD",
            "1VxsEDjo6ZLMT99dpcLu4RQonMDVEQQTG"
        ],
        "total": 3537488,
        "fees": 20000,
        "size": 438,
        "preference": "medium",
        "relayed_by": "",
        "confirmed": "2014-03-26T17:08:04Z",
        "received": "2014-03-26T17:08:04Z",
        "ver": 1,
        "lock_time": 0,
        "double_spend": false,
        "vin_sz": 2,
        "vout_sz": 2,
        "confirmations": 64492,
        "confidence": 1,
        "inputs": [
        {
            "prev_hash": "729f6469b59fea5da7...",
            "output_index": 0,
            "script": "483045022100d06cdad1a...",
            "output_value": 3500000,
            "sequence": 4294967295,
            "addresses": [
                "1VxsEDjo6ZLMT99dpcLu4RQonMDVEQQTG"
            ],
            "script_type": "pay-to-pubkey-hash"
        },
        ...
        ],
        "outputs": [
        {
             "value": 3500000,
             "script": "76a9148629647bd642a237...",
             "addresses": [
                 "1DEP8i3QJCsomS4BSMY2RpU1upv62aGvhD"
             ],
             "script_type": "pay-to-pubkey-hash"
        }
        ]...

        Returns:
            two1.lib.bitcoin.Transaction: a deserialized transaction derived
                from the provided json.

        """

        inputs = []
        outputs = []
        addr_keys = set()
        for i in txn_json["inputs"]:
            # Chain doesn't return the stuff about script length etc, so
            # we need to prepend that.
            script, _ = Script.from_bytes(
                pack_var_str(bytes.fromhex(i["script"])))
            inputs.append(TransactionInput(Hash(i["prev_hash"]),
                                           i["output_index"],
                                           script,
                                           i["sequence"]))
            if "addresses" in i and i["addresses"]:
                addr_keys.add(i["addresses"][0])

        for i in txn_json["outputs"]:
            script, _ = Script.from_bytes(
                pack_var_str(bytes.fromhex(i["script"])))
            outputs.append(TransactionOutput(i["value"],
                                             script))
            if "addresses" in i and i["addresses"]:
                addr_keys.add(i["addresses"][0])

        txn = Transaction(Transaction.DEFAULT_TRANSACTION_VERSION,
                          inputs,
                          outputs,
                          txn_json["lock_time"])

        return txn, addr_keys

    @staticmethod
    def _pop_chunks(lst, chunk_size):
        ret = set(lst[0: chunk_size])
        lst = lst[chunk_size:]
        return ret, lst

    def _request(self, method, path, rate_limit, **kwargs):
        import requests
        if self._session is None:
            self._create_session()

        url = self.server_url + path
        result = None
        try:
            if "params" not in kwargs:
                kwargs["params"] = {}

            kwargs["params"]["token"] = self.api_token

            while True:
                result = self._session.request(method,
                                               url,
                                               **kwargs)

                if result.status_code == 429:
                    if rate_limit:
                       time.sleep(0.8)
                    else:
                        break
                elif result.status_code in (200, 201, 202):
                    break
                else:
                    raise exceptions.DataProviderError("Error occurred during Blockchain provider API ({}).".format(result.status_code))
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
        """ Deprecated Method
        """
        raise NotImplementedError("This method has been deprecated")

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
        min_block = min_block or 0
        address_list_local = address_list[:]
        while address_list_local:
            addresses, address_list_local = self._pop_chunks(address_list_local, self.rate_limit_per_sec )
            r = self._request("GET", "/addrs/{}/full".format(";".join(addresses)),
                              False,
                              params={"limit": 999999999, "after": min_block}
                              )
            return_data = r.json()
            if isinstance(return_data, dict):
                return_data = [return_data, ]
            received_addresses = set()
            for txn_data in return_data:
                if "error" in txn_data:
                    continue
                received_addresses.add(txn_data["address"])
                for txn in filter(lambda x: x["block_height"] >= min_block, txn_data["txs"]):
                    block_hash = None

                    if "block_hash" in txn and txn['block_hash']:
                        block_hash = Hash(txn['block_hash'])
                    metadata = dict(block=txn['block_height'],
                                    block_hash=block_hash,
                                    network_time=timegm(arrow.get(
                                    txn['received']).datetime.timetuple()),
                                    confirmations=txn['confirmations'])

                    txn_obj, addr_keys = self.txn_from_json(txn)
                    for addr in addr_keys:
                        if addr in addresses:
                            ret[addr].append(dict(metadata=metadata,
                                                  transaction=txn_obj))
            remainder = addresses - received_addresses
            address_list_local.extend(remainder)
            if remainder:
                # If the rate limit kicked, sleep for a little bit
                time.sleep(0.8)

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
            r = self._request("GET", "/txs/%s" % txid,
                              True,
                              params={"includeHex": "true", "limit": 999999999}
                              )
            data = r.json()

            block_hash = None
            if "block_hash" in data:
                block_hash = Hash(data['block_hash'])
            metadata = dict(block=data['block_height'],
                            block_hash=block_hash,
                            network_time=timegm(arrow.get(
                                data['received']).datetime.timetuple()),
                            confirmations=data['confirmations'])
            txn, _ = self.txn_from_json(data)
            assert str(txn.hash) == txid

            ret[txid] = dict(metadata=metadata,
                             transaction=txn)

        return ret

    def get_utxos(self, address_list):
        """ Deprecated Method
        """
        raise NotImplementedError("This method has been deprecated")

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

        data = {"tx": signed_hex}
        r = self._request("POST", "/txs/push", True, json=data)
        j = r.json()
        return j["tx"]["hash"]

    def get_block_height(self):
        """ Returns the latest block height

        Returns:
            int: Block height
        """
        r = self._request("GET", "", True)

        ret = None
        data = r.json()
        ret = data['height']

        return ret
