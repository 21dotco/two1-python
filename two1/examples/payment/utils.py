"""Utility functions for payment channels."""

import codecs

from two1.lib.bitcoin.txn import Transaction
from two1.lib.bitcoin.crypto import PublicKey
from two1.lib.bitcoin.utils import bytes_to_str


class PCUtil:

    """Utilities for payment channels."""

    @staticmethod
    def get_redeem_script(transaction):
        """Get the redeem script from a Transaction object."""
        input_script = transaction.inputs[0].script
        multisig_info = input_script.extract_multisig_sig_info()
        return multisig_info['redeem_script']

    @staticmethod
    def public_key_from_hex(hex_string):
        """Convenience function to return a PublicKey object."""
        return PublicKey.from_bytes(codecs.decode(hex_string, 'hex_codec'))

    @staticmethod
    def get_tx_deposit_amount(deposit_tx, refund_tx):
        """Get the multisignature address from a Transaction object."""
        refund_hash160 = PCUtil.get_redeem_script(refund_tx).hash160()
        deposit_index = deposit_tx.output_index_for_address(refund_hash160)

        # Catch lookup errors when trying to find the deposit
        if deposit_index is None:
            return None
        else:
            return deposit_tx.outputs[deposit_index].value

    @staticmethod
    def get_tx_payment_output(payment_tx, public_key):
        """Get payment info from transaction."""
        payment_index = payment_tx.output_index_for_address(
            public_key.hash160())

        # Catch lookup errors when trying to find the payment
        if payment_index is None:
            return None
        else:
            return payment_tx.outputs[payment_index]

    @staticmethod
    def get_tx_public_keys(transaction):
        """Get the public keys from a multisignature Transaction object."""
        redeem_script = PCUtil.get_redeem_script(transaction)
        pubkeys = redeem_script.extract_multisig_redeem_info()['public_keys']
        # TODO lookup merchant public key in database
        res = {
            'customer': PublicKey.from_bytes(pubkeys[0]),
            'merchant': PublicKey.from_bytes(pubkeys[1]),
        }
        return res['customer'], res['merchant']

    @staticmethod
    def parse_tx(tx_hex):
        """Parse a customer transaction.

        Args:
            tx_hex (string): the hexadecimal string representation of a bitcoin
                transaction.

        Returns:
            tx (two1.lib.bitcoin.txn.Transaction): a Transaction object that
            contains the inputs and outputs associated with a bitcoin
            transaction. This operation can be reversed using `serialize_tx`.
        """
        transaction = Transaction.from_hex(tx_hex)
        return transaction

    @staticmethod
    def serialize_tx(tx):
        """Serialize a Transaction object into a hex string.

        Args:
            tx (two1.lib.bitcoin.txn.Transaction): a Transaction object that
            contains the inputs and outputs associated with a bitcoin
            transaction.

        Returns:
            tx_hex (string): the hexadecimal string representation of a bitcoin
                transaction. This can be reversed using `parse_tx`.
        """
        return bytes_to_str(bytes(tx))
