from urllib.parse import urljoin
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

    def _set_url(self):
        self.server_url = urljoin(self.host_name, "blockchain") + "/" + self.chain + "/"
