

class BaseProvider(object):
    """ Abstract base class for any providers of blockchain
        data.
    """

    def __init__(self):
        pass

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
               tuple containing the confirmed and unconfirmed
               balances.
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

    def get_utxo(self, address_list):
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

    def get_balance_hd(self, pub_key, last_payout_index, last_change_index):
        """ Provides the balance for each address.

            Like TransactionDataProvider.get_balance() except that it
            uses the HD public key and returns balances for each
            payout address up to last_payout_index and each change
            address up to last_change_index.

        Args:
            pub_key (HDPublicKey): an extended public key from which
                change and payout addresses are derived.
            last_payout_index (int): Index of last payout address to
                return data for.
            last_change_index (int): Index of last change address to
                return data for.

        Returns:
            dict: A dict keyed by address with each value being a
                tuple containing the confirmed and unconfirmed
                balances.
        """
        raise NotImplementedError

    def get_transactions_hd(self, pub_key, last_payout_index, last_change_index):
        """ Provides transactions associated with each address.

            Like TransactionDataProvider.get_transactions() except
            that it uses the HD public key and returns balances for
            each payout address up to last_payout_index and each
            change address up to last_change_index.

        Args:
            pub_key (HDPublicKey): an extended public key from which
                change and payout addresses are derived.
            last_payout_index (int): Index of last payout address to
                return data for.
            last_change_index (int): Index of last change address to
                return data for.

        Returns:
            dict: A dict keyed by address with each value being a list
                of Transaction objects.
        """
        raise NotImplementedError

    def get_utxo_hd(self, pub_key, last_payout_index, last_change_index):
        """ Provides all unspent transactions associated with each address.

            Like TransactionDataProvider.get_utxo() except that it uses the HD
            public key and returns balances for each payout address up to
            last_payout_index and each change address up to last_change_index.

        Args:
            pub_key (HDPublicKey): an extended public key from which change and
                payout addresses are derived.
            last_payout_index (int): Index of last payout address to
                return data for.
            last_change_index (int): Index of last change address to
                return data for.

        Returns:
            dict: A dict keyed by address with each value being a list
               of UnspentTransactionOutput objects.
        """
        raise NotImplementedError

    def send_transaction(self, transaction):
        """ Broadcasts a transaction to the Bitcoin network

        Args:
            transaction (bytes or str): serialized, signed transaction

        Returns:
            str: The transaction ID
        """
        raise NotImplementedError
