from urllib.parse import urljoin
from two1.lib.blockchain.chain_provider import ChainProvider


class TwentyOneProvider(ChainProvider):
    """ Transaction data provider using the TwentyOne API

        Args:
            // TODO: Use the MachineAuth here to avoid spam
    """

    def __init__(self, twentyone_host_name):
        super().__init__(None, None)
        self.auth = None
        self.server_url = urljoin(twentyone_host_name, "bitcoin") + "/"
