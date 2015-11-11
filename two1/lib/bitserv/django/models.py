from django.db import models


class BlockchainTransaction(models.Model):

    """Record of payments made on the blockchain."""

    txid = models.TextField()
    amount = models.IntegerField()

    class Meta:
        app_label = 'django'


class PaymentChannel(models.Model):

    """State for payment channels."""

    deposit_txid = models.TextField(unique=True)
    state = models.TextField()
    deposit_tx = models.TextField(null=True, blank=True)
    payment_tx = models.TextField(null=True, blank=True)
    refund_tx = models.TextField()
    merchant_pubkey = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    amount = models.IntegerField(null=True, blank=True)
    last_payment_amount = models.IntegerField(null=True, blank=True)

    def __repr__(self):
        """Programmatic representation of the payment channel."""
        return ('<PaymentChannel(deposit_txid: {}, state: {}, amount: {}'
                'expires_at: {}, last_payment_amount: {})>'.format(
                    self.deposit_txid, self.state, self.amount,
                    self.expires_at, self.last_payment_amount))

    class Meta:
        app_label = 'django'


class PaymentChannelSpend(models.Model):

    """Record of payments made within a channel."""
    payment_txid = models.TextField(unique=True)
    payment_tx = models.TextField()
    amount = models.IntegerField()
    is_redeemed = models.BooleanField(default=False)
    deposit_txid = models.TextField()

    def __repr__(self):
        """Programmatic representation of the payment channel spend."""
        return ('<PaymentChannelSpend(payment_txid: {}, amount: {},'
                'is_redeemed: {}, deposit_txid: {})>'.format(
                    self.payment_txid, self.amount, self.is_redeemed,
                    self.deposit_txid))

    class Meta:
        app_label = 'django'
