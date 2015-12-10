"""Wrapper around the two1 wallet for payment channels."""
import codecs
import two1.lib.bitcoin.utils as utils
from two1.lib.bitcoin import Script
from two1.lib.bitcoin import Transaction


class WalletError(Exception):
    pass


class NoMerchantPublicKeyError(WalletError):
    pass


class InvalidPaymentError(WalletError):
    pass


class WalletWrapperBase:

    def __init__(self):
        pass

    def get_public_key(self):
        raise NotImplementedError()

    def sign_half_signed_payment(self):
        raise NotImplementedError()

    def validate_merchant_public_key(self):
        raise NotImplementedError()

###############################################################################


class Two1WalletWrapper(WalletWrapperBase):

    """Wrapper to the Two1 Wallet to provide payment channel functions."""

    def __init__(self, wallet, account='default'):
        """Initialize the wallet."""
        self._wallet = wallet
        self._account = account

    def get_public_key(self):
        """Get a public key for use in a payment channel.

        Returns:
            public_key (string): a string representation of a public key's hex.
        """
        # Get preferred address from our wallet
        pubkey = self._wallet.get_payout_public_key().compressed_bytes
        return codecs.encode(pubkey, 'hex_codec').decode()

    def sign_half_signed_payment(self, payment_tx, redeem_script):
        """Sign a half-signed payment transaction.

        Args:
            payment_tx (two1.lib.bitcoin.txn.Transaction): an object that
                contains a transaction from a customer, whether for a refund
                or general payment, to be signed by the merchant.

        Returns:
            signed_tx (two1.lib.bitcoin.txn.Transaction): an object that
                contains a transaction that has been signed by both the
                customer and the merchant.
        """
        # Verify that the deposit spend has only one input
        if len(payment_tx.inputs) != 1:
            raise InvalidPaymentError('Transaction should have one input.')

        # Get the public and private keys associated with this transaction
        merchant_public_key = redeem_script.merchant_public_key
        private_key = self._wallet.get_private_for_public(merchant_public_key)

        # Sign the first (and only) input in the transaction
        sig = payment_tx.get_signature_for_input(0, Transaction.SIG_HASH_ALL, private_key, redeem_script)[0]

        # Update input script sig
        payment_tx.inputs[0].script.insert(1, sig.to_der() + utils.pack_compact_int(Transaction.SIG_HASH_ALL))

        # Return a Transaction containing the fully-signed transaction.
        return payment_tx

    def validate_merchant_public_key(self, public_key):
        private_key = self._wallet.get_private_for_public(public_key)
        return private_key is not None
