"""Models for Bitcoin Enabled Auth."""

from django.db import models
from rest_framework.authtoken.models import Token


class BitcoinToken(Token):

    """Subclass of DRF Token, with modifications.

    This token "exipires" in sense simlar to an
    oauth token, although instead of "expiring" due
    to a set expiration date, it uses a decrementing
    mechanism that substracts value from the token
    (the cost of an endpoint for an example) until
    the token is no longer valid.

    Inhertited Attributes:
        key = models.CharField(max_length=40,
            primary_key=True)
        user = models.OneToOneField(AUTH_USER_MODEL,
            related_name='auth_token')
        created = models.DateTimeField(auto_now_add=True)

    Attributes:
        balance (int): Satoshi Balance of Token
    """

    balance = models.IntegerField()

    def charge(self, amount):
        """Update the balance if possible.

        Args:
            amount (int): amount to charge balance

        Returns:
            bool: if charge is successful.
        """
        if self.is_solvent(amount):
            self.balance = self.balance - amount
            self.save()
            return True
        else:
            return False

    def is_solvent(self, amount=0):
        """Check if balance is liquid enough.

        Returns:
            bool: if condtion is met.
        """
        return (self.balance - amount) >= 0

    def __repr__(self):
        """repr of BitcoinToken."""
        return "<BitcoinToken(token: {}, balance: {})>".format(
            self.key, self.balance
        )
