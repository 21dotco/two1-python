"""This submodule provides an abstract base class for a Provider, which
provides information about the blockchain and broadcasts transactions by
contacting a server. It is possible to put this "server" on the same local
machine if desired or to keep it remote to save space."""


class BaseProvider(object):
    """ Abstract base class for any providers of blockchain
        data.
    """

    def __init__(self):
        self.can_limit_by_height = False

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
            dict: A dict keyed by address with each value being a
                dict containing the confirmed and total balances.
        """
        raise NotImplementedError

    def get_transactions(self, address_list, limit=100):
        """ Provides transactions associated with each address in address_list.

        Args:
            address_list (list(str)): List of Base58Check encoded
                Bitcoin addresses.
            limit (int): Maximum number of transactions to return.

        Returns:
            dict: A dict keyed by address with each value being a list
                of Transaction objects.
        """
        raise NotImplementedError

    def get_transactions_by_id(self, ids):
        """ Gets transactions by their IDs.

        Args:
            ids (list(str)): List of TXIDs to retrieve.

        Returns:
            dict: A dict keyed by TXID of Transaction objects.
        """
        raise NotImplementedError

    def get_utxos(self, address_list):
        """ Provides all unspent transactions associated with each
        address in address_list.

        Args:
            address_list (list(str)): List of Base58Check encoded
                Bitcoin addresses.

        Returns:
            dict: A dict keyed by address with each value being a list
                of UnspentTransactionOutput objects.
        """
        raise NotImplementedError

    def broadcast_transaction(self, transaction):
        """ Broadcasts a transaction to the Bitcoin network

        Args:
            transaction (bytes or str): serialized, signed transaction

        Returns:
            str: The transaction ID
        """
        raise NotImplementedError
