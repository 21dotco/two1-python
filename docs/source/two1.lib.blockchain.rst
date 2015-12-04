two1.lib.blockchain package
===========================

The blockchain package allows you to receive data about transactions
and blocks from a blockchain data provider, as well as submit new
transactions to the provider for relay to the network and inclusion
in new blocks.

The package is organized around an abstract base class. Users of the 21
Bitcoin Computer will want to use the `TwentyOneProvider` class to
instantiate a connection to the default provider.

Submodules
----------

.. toctree::

    two1.lib.blockchain.submodules

A simple example:

    >>> from two1.lib.blockchain.twentyone_provider import TwentyOneProvider
    >>> provider = TwentyOneProvider()
    >>>
    >>> ## Current block height
    >>> provider.get_block_height()
    386574
    >>>
    >>> ## Get the balance of one or more addresses
    >>> provider.get_balance(['1P8tESXaim9Y58SCd7hyppWcMMB1YSN2r8'])
    {'1P8tESXaim9Y58SCd7hyppWcMMB1YSN2r8': {'confirmed': 520739, 'total': 520739}}
    >>>
    >>> ## Get all the transactions for a particular address
    >>> provider.get_transactions(['1P8tESXaim9Y58SCd7hyppWcMMB1YSN2r8'])
    defaultdict(<class 'list'>, {'1P8tESXaim9Y58SCd7hyppWcMMB1YSN2r8': [{'transaction': <two1.lib.bitcoin.txn.Transaction object at 0x7f1248701f28>, 'metadata': {'block_hash': <two1.lib.bitcoin.hash.Hash object at 0x7f1248701f60>, 'confirmations': 6682, 'block': 379892, 'network_time': 1445436432}}]})
    >>>
    >>> ## Get transactions by their txid
    >>> provider.get_transactions_by_id(['eda100d83ab41b097a707d54f36ea410ef0bd90c7b2ee5392aebca5faf1c0593'])
    {'eda100d83ab41b097a707d54f36ea410ef0bd90c7b2ee5392aebca5faf1c0593': {'transaction': <two1.lib.bitcoin.txn.Transaction object at 0x7f1248709198>, 'metadata': {'block_hash': <two1.lib.bitcoin.hash.Hash object at 0x7f1248709160>, 'confirmations': 6683, 'block': 379892, 'network_time': 1445436432}}}
    >>>
    >>> ## Broadcast a raw transaction; returns a txid
    >>> provider.broadcast_transaction('010000000193051caf5fcaeb2a39e52e7b0cd90bef10a46ef3547d707a091bb43ad800a1ed010000006b483045022100e91f0060f892047ae5782c307eaf26f3df5d2384f7ea01366b77ea9e39e0337002203c6d6ed097cb6eada8ac3869a08eae7fa31b97017cace121b07c602bc1c03a0d0121026a55ca7ad4ff198c17af11cc06208cf3337d6a3256172748c208327cb8158b69ffffffff0123f20700000000001976a9146c6bddd91f2e0ad0f4d35a8e79a2a544019ab22388ac00000000')
    '028bb132e633f13734c33b72bdb21f339e17211a8d5ebff4373721336d897425'
