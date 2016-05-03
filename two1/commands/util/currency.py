"""Utility for making conversions among various currencies."""
from two1.commands.util import exceptions


def create_default_rest_client():
    """Return a rest client using default parameters."""
    import two1
    from two1 import wallet
    from two1.commands.util import config
    from two1.server import machine_auth_wallet, rest_client
    auth = machine_auth_wallet.MachineAuthWallet(wallet.Wallet())
    return rest_client.TwentyOneRestClient(two1.TWO1_HOST, auth, config.Config().username)


class Price:

    """An object that knows exchange rates and how to convert amounts."""

    SAT = 'satoshis'
    BTC = 'bitcoins'
    USD = 'usd'
    DENOMINATIONS = ", ".join([SAT, BTC, USD])

    SAT_TO_BTC = 1 / 1e8

    def __init__(self, amount, denomination=SAT, rest_client=None):
        """Return a new Price object with the provided amount."""
        if amount < 0:
            raise exceptions.Two1Error('Parameter `amount` must be a positive number.')
        if denomination.lower() in Price.SAT:
            self.denomination = Price.SAT
        elif denomination.lower() in Price.BTC:
            if amount < Price.SAT_TO_BTC:
                raise exceptions.Two1Error('Bitcoin amount must be larger than 1e-8')
            self.denomination = Price.BTC
        elif denomination.lower() in Price.USD:
            self.denomination = Price.USD
        else:
            raise exceptions.Two1Error('Unknown denomination: {}.\nValid denominations: {}.'.format(denomination, Price.DENOMINATIONS))
        self.amount = amount
        self.rest_client = rest_client if rest_client else create_default_rest_client()

    @staticmethod
    def exchange_rate(src, dst):
        """Get the current exchange rate between two currencies."""
        return getattr(Price(1, src), dst)

    def _get_usd_rate(self, amount=1e8):
        """Rest client binding to return only the requested dollar amount."""
        quote = self.rest_client.quote_bitcoin_price(amount)
        if not quote.ok:
            raise Exception('Error getting bitcoin quote from server.')
        return quote.json()['price']

    @property
    def satoshis(self):
        """Return the standardized integer amount in satoshis."""
        if self.denomination == Price.SAT:
            return round(self.amount)
        elif self.denomination == Price.BTC:
            return round(self.amount / Price.SAT_TO_BTC)
        elif self.denomination == Price.USD:
            return round(self.amount / self._get_usd_rate() / Price.SAT_TO_BTC)

    @property
    def bitcoins(self):
        """Return the price in bitcoin as a float to 8 decimal places."""
        if self.denomination == Price.BTC:
            return self.amount
        return self.satoshis * Price.SAT_TO_BTC

    @property
    def usd(self):
        """Return the price in dollars as a float to 2 decimal places."""
        if self.denomination == Price.USD:
            return self.amount
        return self._get_usd_rate(self.satoshis)
