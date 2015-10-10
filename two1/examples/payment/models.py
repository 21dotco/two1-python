"""Models to represent data involved in Payment Channels."""

from pytz import utc
from django.db import models
from datetime import datetime


class PublicKey(models.Model):

    """Stores abstract information about a customer address."""

    hex_string = models.CharField(max_length=256)

    def __repr__(self):
        """Expressive representation of a PublicKey."""
        return 'PublicKey(hex_string: {})'.format(self.hex_string)

    def __str__(self):
        """Simple string representation of a PublicKey."""
        return self.hex_string


class Channel(models.Model):

    """Stores information about to a payment channel."""

    OPENING = 'op'                  # Connecting and negotating refund tx
    CONFIRMING = 'cf'               # Waiting for deposit tx confirmation
    READY = 'rd'                    # Ready for payment tx
    CLOSING = 'ci'                  # Negotiating close with server
    PAYING = 'pa'                   # Waiting for payment tx confirmation
    REFUNDING = 're'                # Waiting for refund tx confirmation
    CLOSED = 'cl'                   # Payment tx / refund tx confirmed
    STATUS_TYPES = ((OPENING, 'opening'), (CONFIRMING, 'confirming'),
                    (READY, 'ready'), (CLOSING, 'closing'), (PAYING, 'paying'),
                    (REFUNDING, 'refunding'), (CLOSED, 'closed'))

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField()
    deposit_tx_id = models.CharField(max_length=256)
    customer = models.ForeignKey(PublicKey, related_name='c_channels')
    merchant = models.ForeignKey(PublicKey, related_name='m_channels')
    status = models.CharField(
        max_length=2, choices=STATUS_TYPES, default=OPENING
    )

    def __repr__(self):
        """Expressive representation of a Channel."""
        return ('<Channel(status: {}, customer: {}, merchant: {}, '
                'created_at: {}, expires_at: {})>'.format(
                    self.get_status_display(), self.customer, self.merchant,
                    self.created_at, self.expires_at))

    def __str__(self):
        """Simple string representation of a Channel."""
        return self.deposit_tx_id

    @property
    def deposit(self):
        """Get the customer's deposit which initialized the channel."""
        try:
            return self.transactions.get(category=Transaction.DEPOSIT)
        except Transaction.DoesNotExist:
            return None

    @property
    def refund(self):
        """Get the customer's refund which terminates the channel."""
        try:
            return self.transactions.get(category=Transaction.REFUND)
        except Transaction.DoesNotExist:
            return None

    @property
    def payment(self):
        """Get the current payment to be made in the channel."""
        try:
            return self.transactions.get(category=Transaction.PAYMENT)
        except Transaction.DoesNotExist:
            return None

    @property
    def last_payment(self):
        """Get the previous payment made in the channel."""
        try:
            return self.transactions.get(category=Transaction.LAST_PAYMENT)
        except Transaction.DoesNotExist:
            return None

    @property
    def last_payment_amount(self):
        """Get the incremental amount in satoshis of the last payment."""
        last = self.last_payment.amount if self.last_payment else 0
        current = self.payment.amount if self.payment else 0
        return current - last

    @property
    def customer_balance(self):
        """Get the current customer balance remaining in the channel."""
        deposit_amount = self.deposit.amount
        current_payment = 0

        if self.payment:
            current_payment = self.payment.amount

        return deposit_amount - current_payment

    def update_status(self):
        """Update the current status of the channel."""
        payment = self.payment
        refund = self.refund
        deposit = self.deposit

        # A payment transaction has been broadcast
        if payment and payment.is_broadcast:
            if payment.is_confirmed:
                self.status = self.CLOSED
            else:
                self.status = self.CLOSING

        # A refund transaction has been broadcast
        elif refund and refund.is_broadcast:
            self.status = self.REFUNDING

        # A deposit transaction has been broadcast
        elif deposit and deposit.is_broadcast:
            if deposit.is_confirmed:
                self.status = self.READY
            else:
                self.status = self.CONFIRMING

        # No transactions exist
        else:
            self.status = self.OPENING

        self.save()

    @property
    def time_left(self):
        """Get the time left before the channel expires."""
        now = datetime.utcnow().replace(tzinfo=utc)
        return self.expires_at - now

    def save_new_payment(self, **kwargs):
        """Save new payment and cache or discard old payments."""
        # Delete the oldest transaction if there is one
        if self.last_payment:
            self.last_payment.delete()

        # If there is a current payment, we cache it as the *new* last payment
        if self.payment:
            self.payment.save_as_last_payment()

        # Save the new payment as the current payment
        _default_kwargs = {'channel': self, 'category': Transaction.PAYMENT}
        kwargs.update(_default_kwargs)
        payment = Transaction(**kwargs)
        payment.save()


class Transaction(models.Model):

    """Stores information about a transaction made on the blockchain."""

    DEPOSIT = 'dp'  # Initializes a payment channel
    PAYMENT = 'py'  # Interim payment, terminates a payment channel by merchant
    LAST_PAYMENT = 'lp'  # Last payment stored for data consistency
    REFUND = 'rf'  # Terminates a payment channel by customer (after timeout)
    CATEGORY_TYPES = ((DEPOSIT, 'deposit'), (REFUND, 'refund'),
                      (PAYMENT, 'payment'), (LAST_PAYMENT, 'last_payment'))

    transaction_id = models.CharField(max_length=256)
    transaction_hex = models.CharField(max_length=1024)
    amount = models.FloatField()
    channel = models.ForeignKey(Channel, related_name='transactions')
    category = models.CharField(max_length=2, choices=CATEGORY_TYPES)
    is_broadcast = models.BooleanField(default=False)
    is_confirmed = models.BooleanField(default=False)
    is_redeemed = models.BooleanField(default=False)

    def __repr__(self):
        """Expressive representation of a Transaction."""
        return ('<Transaction(transaction_id: {}, amount: {}, channel: {}, '
                'category: {}, is_broadcast: {}, is_confirmed: {}, '
                'is_redeemed: {})>'.format(
                    self.transaction_id, self.amount, self.channel,
                    self.get_category_display(), self.is_broadcast,
                    self.is_confirmed, self.is_redeemed))

    def __str__(self):
        """Simple string representation of a Transaction."""
        return self.transaction_id

    def broadcast(self):
        """Indicate that the transaction has been broadcast to the network."""
        self.is_broadcast = True
        self.save()
        self.channel.update_status()

    def confirm(self):
        """Indicate that the transaction has been confirmed on the network."""
        self.is_broadcast = True
        self.is_confirmed = True
        self.save()
        self.channel.update_status()

    def redeem(self):
        """Indicate that the transaction has been redeemed by the merchant."""
        self.is_redeemed = True
        self.save()

    def save_as_last_payment(self):
        """Cache this payment as the last one made before the current."""
        self.category = self.LAST_PAYMENT
        self.save()
