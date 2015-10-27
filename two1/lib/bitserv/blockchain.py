"""Blockchain provider for payment channels."""

import requests


class BlockchainError(Exception):
    pass


class BlockchainServerError(BlockchainError):
    pass


class InsightBlockchain:

    """Blockchain provider using Insight."""

    def __init__(self, base_url):
        """Initialize the blockchain provider."""
        super().__init__()
        self._base_url = base_url

    def broadcast(self, tx):
        """Broadcast transaction to the blockchain."""
        r = requests.post(self._base_url + "/api/tx/send", data={'rawtx': tx})
        if r.status_code != 200:
            raise BlockchainServerError(
                "Broadcasting transaction: Status Code {}, {}".format(
                    r.status_code, r.text))

        return r.json()['txid']


class MockBlockchain:

    """Blockchain provider for tests."""

    def broadcast(self, tx):
        """Mock broadcast."""
        return tx
