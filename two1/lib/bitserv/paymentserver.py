"""Tools for Payment Channels."""

import codecs
from two1.lib.bitcoin.crypto import PublicKey

from .wallet import Two1WalletWrapper
from .wallet import get_redeem_script, get_tx_public_keys
from .channel_data import DatabaseSQLite3
from .blockchain import InsightBlockchain


class PaymentServerError(Exception):
    pass


class InvalidPaymentError(PaymentServerError):
    pass


class RedeemPaymentError(PaymentServerError):
    pass


class ChannelClosedError(PaymentServerError):
    pass


class PaymentBroadcastError(PaymentServerError):
    pass


class PaymentServerNotFoundError(PaymentServerError):
    pass


class BadTransactionError(PaymentServerError):
    pass


class PaymentServer:

    """Payment channel handling.

    This class handles the server-side implementation of payment channels from
    handshake to channel close. It also implements the ability for
    """

    # Minimum transaction fee and total payment amount (dust limit)
    MIN_TX_FEE = 5000
    DUST_LIMIT = 546

    def __init__(self, wallet, account='default', testnet=False,
                 blockchain=None, db=None):
        """Initalize the payment server.

        Args:
            wallet (.wallet.Two1WalletWrapper): a two1 wallet wrapped with
                payment server functionality.
            account (string): which account within the wallet to use (e.g.
                'merchant', 'customer', 'default', etc).
            testnet (boolean): whether or not the server should broadcast and
                verify transactions against the bitcoin testnet blockchain.
        """
        self._wallet = Two1WalletWrapper(wallet, account)
        self._blockchain = blockchain
        self._db = db
        if db is None:
            self._db = DatabaseSQLite3()
        if blockchain is None:
            self._blockchain = InsightBlockchain(
                'https://blockexplorer.com' if not testnet
                else 'https://testnet.blockexplorer.com')

    def discovery(self):
        """Return the merchant's public key.

        A customer requests a public key from a merchant. This allows the
        customer to create a multi-signature refund transaction with both the
        customer and merchant's public keys.
        """
        return self._wallet.get_public_key()

    def initialize_handshake(self, refund_tx):
        """Initialize a payment channel.

        The customer initializes the payment channel by providing a half-signed
        multi-signature refund transaction. This allows the merchant to return
        a fully executed refund transaction.

        Args:
            refund_tx (two1.lib.bitcoin.txn.Transaction): half-signed refund
                Transaction from a customer. This object is passed by reference
                and modified directly.

        Returns:
            (boolean): whether the handshake was successfully initialized.
        """
        # Verify that the transaction is what we expect
        self._wallet.verify_half_signed_tx(refund_tx)

        # Sign the remaining half of the transaction
        self._wallet.sign_half_signed_tx(refund_tx)

        # Try to create the channel and verify that the deposit txid is good
        deposit_txid = str(refund_tx.inputs[0].outpoint)
        cust_key, merch_key = get_tx_public_keys(refund_tx)
        try:
            self._db.pc.create(refund_tx, merch_key)
        except:
            raise BadTransactionError(
                'That deposit has already been used to create a channel.')

        return True

    def complete_handshake(self, deposit_txid, deposit_tx):
        """Complete the final step in the channel handshake.

        The customer completes the handshake by sending the merchant the
        customer's signed deposit transaction, which the merchant can then
        broadcast to the network. The merchant responds with 200 to verify that
        the handshake has completed successfully.

        Args:
            deposit_txid (string): string representation of the deposit
                transaction hash. This is used to look up the payment channel.
            deposit_tx (two1.lib.bitcoin.txn.Transaction): half-signed deposit
                Transaction from a customer. This object is passed by reference
                and modified directly.

        Returns:
            (boolean): whether the handshake was successfully completed.
        """
        try:
            channel = self._db.pc.lookup(deposit_txid)
        except:
            raise PaymentServerNotFoundError('Related channel not found.')

        # Get the refund spend address
        refund_tx = channel['refund_tx']

        # Find the payment amount associated with the refund
        refund_hash160 = get_redeem_script(refund_tx).hash160()
        deposit_index = deposit_tx.output_index_for_address(refund_hash160)

        # Verify that the deposit funds the refund in our records
        if deposit_index is not None:
            deposit_amt = deposit_tx.outputs[deposit_index].value
        else:
            raise BadTransactionError('Deposit must fund refund.')

        # Save the deposit transaction
        try:
            self._db.pc.update_deposit(deposit_txid, deposit_tx, deposit_amt)
        except:
            raise BadTransactionError('Deposit already used.')

        # TODO: Broadcast the deposit transaction
        self._db.pc.update_state(deposit_txid, 'confirming')

        return True

    def receive_payment(self, deposit_txid, payment_tx):
        """Receive and process a payment within the channel.

        The customer makes a payment in the channel by sending the merchant a
        half-signed payment transaction. The merchant signs the other half of
        the transaction and saves it in its records (but does not broadcast it
        or send it to the customer). The merchant responds with 200 to verify
        that the payment was handled successfully.

        Args:
            deposit_txid (string): string representation of the deposit
                transaction hash. This is used to look up the payment channel.
            deposit_tx (two1.lib.bitcoin.txn.Transaction): half-signed deposit
                Transaction from a customer. This object is passed by reference
                and modified directly.

        Returns:
            (boolean): whether the payment was sucessfully processed.
        """
        # Verify that the transaction is what we expect
        self._wallet.verify_half_signed_tx(payment_tx)

        # Get channel and addresses related to the deposit
        try:
            channel = self._db.pc.lookup(deposit_txid)
        except:
            raise PaymentServerNotFoundError('Related channel not found.')

        # Get merchant public key information from payment channel
        last_pmt_amt = channel['last_payment_amount']
        merch = channel['merchant_pubkey']
        merch_pubkey = PublicKey.from_bytes(codecs.decode(merch, 'hex_codec'))
        index = payment_tx.output_index_for_address(merch_pubkey.hash160())

        # Verify that the payment channel is still open
        if (channel['state'] != 'confirming' and channel['state'] != 'ready'):
            raise ChannelClosedError('Payment channel closed.')

        # Find the payment amount associated with the merchant address
        if index is None:
            raise BadTransactionError('Payment must pay to merchant pubkey.')

        # Validate that the payment is more than the last one
        new_pmt_amt = payment_tx.outputs[index].value
        if new_pmt_amt <= last_pmt_amt:
            raise BadTransactionError('Micropayment must be greater than 0.')

        # Verify that the payment channel is still open
        if (channel['state'] != 'confirming' and channel['state'] != 'ready'):
            raise ChannelClosedError('Payment channel closed.')

        # Verify that the transaction has adequate fees
        net_pmt_amount = sum([d.value for d in payment_tx.outputs])
        deposit_amount = channel['amount']
        if deposit_amount < net_pmt_amount + PaymentServer.MIN_TX_FEE:
            raise BadTransactionError('Payment must have adequate fees.')

        # Verify that both payments are not below the dust limit
        for payment in payment_tx.outputs:
            if payment.value < PaymentServer.DUST_LIMIT:
                raise BadTransactionError(
                    'Final payment must have outputs greater than {}.'.format(
                        PaymentServer.DUST_LIMIT))

        # TODO Verify that the redeem script is the same as the last payment

        # Sign the remaining half of the transaction
        self._wallet.sign_half_signed_tx(payment_tx)

        # Update the current payment transaction
        self._db.pc.update_payment(deposit_txid, payment_tx, new_pmt_amt)
        self._db.pmt.create(deposit_txid, payment_tx, new_pmt_amt-last_pmt_amt)

        return True

    def status(self, deposit_txid):
        """Get a payment channel's current status.

        Args:
            deposit_txid (string): string representation of the deposit
                transaction hash. This is used to look up the payment channel.
        """
        try:
            channel = self._db.pc.lookup(deposit_txid)
        except:
            raise PaymentServerNotFoundError('Related channel not found.')

        return {'status': channel['state'],
                'balance': channel['last_payment_amount'],
                'time_left': channel['expires_at']}

    def close(self, deposit_txid):
        """Close a payment channel.

        Args:
            deposit_txid (string): string representation of the deposit
                transaction hash. This is used to look up the payment channel.
            txid_signature (string): a signed message consisting solely of the
                deposit_txid to verify the authenticity of the close request.
        """
        try:
            channel = self._db.pc.lookup(deposit_txid)
        except:
            raise PaymentServerNotFoundError('Related channel not found.')

        # Verify that there is a valid payment to close
        if not channel['payment_tx']:
            raise BadTransactionError('No payments made in channel.')

        # Broadcast payment transaction to the blockchain
        self._blockchain.broadcast(channel['payment_tx'].to_hex())

        # Record the broadcast in the database
        self._db.pc.update_state(deposit_txid, 'closed')

        return str(channel['payment_tx'].hash)

    def redeem(self, payment_txid):
        """Determine the validity and amount of a payment.

        Args:
            payment_txid (string): the hash in hexadecimal of the payment
                transaction, often referred to as the transaction id.

        Returns:
            pmt_amount (int): value in satoshis of the incremental payment.

        Raises:
            PaymentError: reason why payment is not redeemable.
        """
        # Verify that we have this payment transaction saved
        try:
            payment = self._db.pmt.lookup(payment_txid)
        except:
            raise PaymentServerNotFoundError('Payment not found.')

        # Verify that this payment exists within a channel (do we need this?)
        try:
            channel = self._db.pc.lookup(payment['deposit_txid'])
        except:
            raise PaymentServerNotFoundError('Channel not found.')

        # Verify that the payment channel is still open
        if (channel['state'] != 'confirming' and channel['state'] != 'ready'):
            raise ChannelClosedError('Payment channel closed.')

        # Verify that the most payment has not already been redeemed
        if payment['is_redeemed']:
            raise RedeemPaymentError('Payment already redeemed.')

        # Calculate and redeem the current payment
        self._db.pmt.redeem(payment_txid)
        return payment['amount']
