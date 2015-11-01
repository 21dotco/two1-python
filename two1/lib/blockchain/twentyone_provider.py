from calendar import timegm
from collections import defaultdict

import arrow


from urllib.parse import urljoin
from two1.lib.bitcoin.hash import Hash
from two1.lib.blockchain.chain_provider import ChainProvider


class TwentyOneProvider(ChainProvider):
    """ Transaction data provider using the TwentyOne API

        Args:
            // TODO: Use the MachineAuth here to avoid spam
    """
    DEFAULT_HOST = "https://dotco-devel-pool2.herokuapp.com"

    def __init__(self, twentyone_host_name=DEFAULT_HOST, testnet=False,
                 connection_pool_size=0):
        self.host_name = twentyone_host_name

        super().__init__(None, None, testnet,
                         connection_pool_size=connection_pool_size)
        self.testnet = testnet
        self.auth = None
        self.can_limit_by_height = True

    def _set_url(self):
        self.server_url = urljoin(self.host_name, "blockchain") + "/" + self.chain + "/"

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
            path = "addresses/" + ",".join(addresses) \
                   + "/transactions?limit={}".format(limit)
            if min_block:
                path += "&min_block={}".format(min_block)

            r = self._request("GET", path)
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
