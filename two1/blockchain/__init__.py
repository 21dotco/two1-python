# flake8: noqa
"""The blockchain module within the 21 Blockchain Library allows you to receive
data about transactions and blocks from a blockchain data provider, as well as
submit new transactions to the provider for relay to the network and inclusion
in new blocks.

The package is organized around an abstract base class. Users of the 21 Bitcoin
Computer will want to use the `TwentyOneProvider` class to instantiate a
connection to the default provider."""
from .twentyone_provider import TwentyOneProvider
