import decimal


satoshi_to_btc = decimal.Decimal(1e8)
btc_to_satoshi = 1 / satoshi_to_btc


def convert_to_satoshis(btc):
    """ Converts an amount in BTC to satoshis.

    This function takes care of rounding and quantization issues
    (i.e. IEEE-754 precision/representation) and guarantees the
    correct BTC value. Specifically, any floating point digits
    beyond 1e-8 will be rounded to the nearest satoshi.

    Args:
        btc (float): Amount in BTC.

    Returns:
        int: Amount in satoshis.
    """
    # First truncate trailing digits
    q = decimal.Decimal(btc).quantize(btc_to_satoshi)
    satoshis = int((q * satoshi_to_btc).to_integral_value())

    c = decimal.Decimal(satoshis / satoshi_to_btc).quantize(btc_to_satoshi)
    if c != q:
        raise ValueError("Improper rounding or quantization.")

    return satoshis


def convert_to_btc(satoshis):
    """ Converts an amount in satoshis to BTC.

    The return value of this function should only
    be used for display purposes. All internal calculations
    should be done using satoshis (integers)

    Args:
        satoshis (int): Amount in satoshis

    Returns:
        decimal: Amount in BTC
    """
    if not isinstance(satoshis, int):
        raise TypeError("satoshis must be an integer.")

    return decimal.Decimal(satoshis) / satoshi_to_btc


class BaseWallet(object):
    """ An abstract wallet class.
    """

    """ The configuration options available for the wallet.

        The keys of this dictionary are the available configuration
        settings/options for the wallet. The value for each key
        represents the possible values for each option.
        e.g. {key_style: ["HD","Brain","Simple"], ....}
    """
    config_options = {}

    @staticmethod
    def is_configured():
        """ Returns the configuration/initialization status of the
        wallet.

        Returns:
            bool:
                True if the wallet has been configured and ready to
                use otherwise False
        """
        raise NotImplementedError('Abstract class, `is_configured` must be overridden')

    @staticmethod
    def configure(config_options):
        """ Automatically configures the wallet with the provided configuration options
        """
        raise NotImplementedError('Abstract class, `auto_configure` must be overridden')

    def __init__(self):
        super(BaseWallet, self).__init__()

    @property
    def addresses(self):
        """ Gets the address list for the current wallet.

        Returns:
            list: The current list of addresses in this wallet.
        """
        raise NotImplementedError('Abstract class, `addresses` must be overridden')

    @property
    def current_address(self):
        """ Gets the preferred address.

        Returns:
            str: The current preferred payment address.
        """
        raise NotImplementedError('Abstract class, `current_address` must be overridden')

    def balance(self):
        """ Gets the confirmed balance of the wallet in Satoshi.

        Returns:
            number: The current confirmed balance.
        """
        return self.confirmed_balance()

    def confirmed_balance(self):
        """ Gets the current confirmed balance of the wallet in Satoshi.

        Returns:
            number: The current confirmed balance.
        """
        raise NotImplementedError('Abstract class `confirmed_balance` must be overridden')

    def unconfirmed_balance(self):
        """ Gets the current unconfirmed balance of the wallet in Satoshi.

        Returns:
            number: The current unconfirmed balance.
        """
        raise NotImplementedError('Abstract class, `unconfirmed_balance` must be overridden')

    def broadcast_transaction(self, tx):
        """ Broadcasts the transaction to the Bitcoin network.

        Args:
            tx (str): Hex string serialization of the transaction
               to be broadcasted to the Bitcoin network..
        Returns:
            str: The name of the transaction that was broadcasted.
        """
        raise NotImplementedError('Abstract class, `broadcast_transaction` must be overridden')

    def make_signed_transaction_for(self, address, amount):
        """ Makes a raw signed unbrodcasted transaction for the specified amount.

        Args:
            address (str): The address to send the Bitcoin to.
            amount (number): The amount of Bitcoin to send.
        Returns:
            list(dict): A list of dicts containing transaction names
            and raw transactions.  e.g.: [{"txid": txid0, "txn":
            txn_hex0}, ...]
        """
        raise NotImplementedError('Abstract class, `make_signed_transaction_for` must be overridden')

    def send_to(self, address, amount):
        """ Sends Bitcoin to the provided address for the specified amount.

        Args:
            address (str): The address to send the Bitcoin to.
            amount (number): The amount of Bitcoin to send.
        Returns:
            list(dict): A list of dicts containing transaction names
            and raw transactions.  e.g.: [{"txid": txid0, "txn":
            txn_hex0}, ...]
        """
        raise NotImplementedError('Abstract class, `send_to` must be overridden')
