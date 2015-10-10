"""Tools for Payment Channels."""

import codecs
from pytz import utc
from datetime import datetime

from .utils import PCUtil
from .wallet import Two1WalletWrapper
from .blockchain import InsightBlockchain
from two1.examples.payment.models import Channel, PublicKey, Transaction


class PaymentServerError(Exception):
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
                 blockchain=None):
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

        # Get public keys for the transaction
        cust_keys, merch_keys = PCUtil.get_tx_public_keys(refund_tx)

        # Save the customer's public key
        customer_address, _ = PublicKey.objects.get_or_create(
            hex_string=codecs.encode(
                cust_keys.compressed_bytes, 'hex_codec'))
        merchant_address, _ = PublicKey.objects.get_or_create(
            hex_string=codecs.encode(
                merch_keys.compressed_bytes, 'hex_codec'))

        # Use lock_time to set refund expiration date
        lock_time = datetime.utcfromtimestamp(refund_tx.lock_time)
        expiration_time = lock_time.replace(tzinfo=utc)

        # Create a new payment channel that expires 24 hours from now
        channel, created = Channel.objects.get_or_create(
            deposit_tx_id=str(refund_tx.inputs[0].outpoint),
            defaults={
                'customer': customer_address,
                'merchant': merchant_address,
                'expires_at': expiration_time,
            }
        )
        # Verify that this deposit transaction hasn't already been used
        if not created:
            raise BadTransactionError(
                'That deposit has already been used to create a channel.')

        # Save the refund transaction
        transaction, created = Transaction.objects.get_or_create(
            transaction_id=str(refund_tx.hash),
            category=Transaction.REFUND,
            defaults={
                'transaction_hex': PCUtil.serialize_tx(refund_tx),
                'amount': sum([d.value for d in refund_tx.outputs]),
                'channel': channel,
            }
        )
        # Check to make sure the refund hasn't already been used
        if not created:
            raise BadTransactionError(
                'That refund transaction has already been used.')

        return True

    def complete_handshake(self, deposit_tx_id, deposit_tx):
        """Complete the final step in the channel handshake.

        The customer completes the handshake by sending the merchant the
        customer's signed deposit transaction, which the merchant can then
        broadcast to the network. The merchant responds with 200 to verify that
        the handshake has completed successfully.

        Args:
            deposit_tx_id (string): string representation of the deposit
                transaction hash. This is used to look up the payment channel.
            deposit_tx (two1.lib.bitcoin.txn.Transaction): half-signed deposit
                Transaction from a customer. This object is passed by reference
                and modified directly.

        Returns:
            (boolean): whether the handshake was successfully completed.
        """
        try:
            channel = Channel.objects.get(deposit_tx_id=deposit_tx_id)
        except:
            raise PaymentServerNotFoundError('Related channel not found.')

        if not channel.refund:
            raise PaymentServerNotFoundError('Channel refund not found.')

        # Get the refund spend address
        refund_tx = PCUtil.parse_tx(channel.refund.transaction_hex)

        # Find the payment amount associated with the merchant address
        deposit_amount = PCUtil.get_tx_deposit_amount(deposit_tx, refund_tx)

        # Verify that the deposit funds the refund in our records
        if deposit_amount is None:
            raise BadTransactionError('Deposit must fund refund.')

        # Save the deposit transaction
        deposit, created = Transaction.objects.get_or_create(
            transaction_id=deposit_tx_id,
            category=Transaction.DEPOSIT,
            defaults={
                'transaction_hex': PCUtil.serialize_tx(deposit_tx),
                'amount': deposit_amount,
                'channel': channel,
            }
        )

        # Final check to make sure the deposit hasn't already been used
        if not created:
            raise BadTransactionError('Deposit already used in a channel.')

        # TODO: Broadcast the deposit transaction
        deposit.broadcast()

        return True

    def receive_payment(self, deposit_tx_id, payment_tx):
        """Receive and process a payment within the channel.

        The customer makes a payment in the channel by sending the merchant a
        half-signed payment transaction. The merchant signs the other half of
        the transaction and saves it in its records (but does not broadcast it
        or send it to the customer). The merchant responds with 200 to verify
        that the payment was handled successfully.

        Args:
            deposit_tx_id (string): string representation of the deposit
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
            deposit = Transaction.objects.get(
                transaction_id=deposit_tx_id,
                category=Transaction.DEPOSIT
            )
            channel = deposit.channel
        except:
            raise PaymentServerNotFoundError('Related channel not found.')

        merchant_pubkey = PCUtil.public_key_from_hex(
            channel.merchant.hex_string)

        # Verify that the payment channel is still open
        if (channel.status != Channel.CONFIRMING and
                channel.status != Channel.READY):
            raise ChannelClosedError('Payment channel closed.')

        # Find the payment amount associated with the merchant address
        transaction_output = PCUtil.get_tx_payment_output(
            payment_tx, merchant_pubkey)

        # Verify that the payment has adequate fees
        if transaction_output is None:
            raise BadTransactionError('Payment must pay to merchant pubkey.')

        transaction_amount = transaction_output.value

        # Verify that the transaction has adequate fees
        net_tx_amount = sum([d.value for d in payment_tx.outputs])
        if channel.deposit.amount < net_tx_amount + PaymentServer.MIN_TX_FEE:
            raise BadTransactionError('Payment must have adequate fees.')

        # Verify that both payments are not below the dust limit
        for payment in payment_tx.outputs:
            if payment.value < PaymentServer.DUST_LIMIT:
                raise BadTransactionError(
                    'Final payment must have outputs greater than {}.'.format(
                        PaymentServer.DUST_LIMIT))

        # TODO Verify that the redeem script is the same as the last payment

        # Throw an error if this payment is not greater than the current
        if channel.payment:
            if transaction_amount <= channel.payment.amount:
                raise BadTransactionError(
                    'Micropayments must be greater than 0 satoshi.')

        # Sign the remaining half of the transaction
        self._wallet.sign_half_signed_tx(payment_tx)

        # Save current payment into last payment model, if needed
        channel.save_new_payment(
            transaction_id=str(payment_tx.hash),
            transaction_hex=PCUtil.serialize_tx(payment_tx),
            amount=transaction_amount,
        )

        return True

    def status(self, deposit_tx_id):
        """Get a payment channel's current status.

        Args:
            deposit_tx_id (string): string representation of the deposit
                transaction hash. This is used to look up the payment channel.
        """
        deposit = Transaction.objects.get(
            transaction_id=deposit_tx_id,
            category=Transaction.DEPOSIT
        )
        channel = deposit.channel

        recent_payment = None
        if channel.payment:
            recent_payment = channel.payment.transaction_id

        return {
            'status': channel.get_status_display(),
            'balance': channel.customer_balance,
            'time_left': channel.time_left,
            'recent_payment': recent_payment,
        }

    def close(self, deposit_tx_id):
        """Close a payment channel.

        Args:
            deposit_tx_id (string): string representation of the deposit
                transaction hash. This is used to look up the payment channel.
            txid_signature (string): a signed message consisting solely of the
                deposit_tx_id to verify the authenticity of the close request.
        """
        deposit = Transaction.objects.get(
            transaction_id=deposit_tx_id,
            category=Transaction.DEPOSIT
        )
        channel = deposit.channel

        # Verify that there is a valid payment to close
        if not channel.payment:
            raise BadTransactionError('No payments made in channel.')

        # Broadcast payment transaction to the blockchain
        self._blockchain.broadcast(channel.payment.transaction_hex)

        # Record the broadcast in the database
        channel.payment.broadcast()

        return channel.payment.transaction_id

    @staticmethod
    def redeem(payment_tx_id):
        """Determine the validity and amount of a payment.

        Args:
            payment_tx_id (string): the hash in hexadecimal of the payment
                transaction, often referred to as the transaction id.

        Returns:
            pmt_amount (int): value in satoshis of the incremental payment.

        Raises:
            PaymentError: reason why payment is not redeemable.
        """
        # Verify that we have this payment within the channel.
        try:
            requested_payment = Transaction.objects.get(
                transaction_id=payment_tx_id
            )
        except:
            raise RedeemPaymentError('Not/no longer available in channel.')

        # Get the associated channel and its most recent payment
        channel = requested_payment.channel
        current_payment = channel.payment

        # Verify that we are redeeming the most recent payment
        if payment_tx_id != current_payment.transaction_id:
            raise RedeemPaymentError('Not the most recent payment.')

        # Verify that the most recent payment has not already been redeemed
        if current_payment.is_redeemed:
            raise RedeemPaymentError('Already redeemed.')

        # Calculate and redeem the current payment
        pmt_amount = channel.last_payment_amount
        current_payment.redeem()

        return pmt_amount


def get_pc_public_key():
    """Get a public key for use in a payment channel.

    Args:
        None

    Returns:
        public_key (string): a string representation of a public key's hex.
    """
    # Get preferred address from our wallet
    pubkey = wallet.get_change_public_key().compressed_bytes
    public_key = binascii.hexlify(pubkey).decode('utf-8')

    return public_key


def _get_multisig_info(transaction):
    """Get the redeem script from a Transaction object."""
    input_script = transaction.inputs[0].script
    redeem_script = input_script.extract_multisig_sig_info()
    return redeem_script


def get_deposit_amount_from_tx(deposit_tx, refund_tx):
    """Get the multisignature address from a Transaction object."""
    multisig_info = _get_multisig_info(refund_tx)
    refund_hash160 = multisig_info['redeem_script'].hash160()
    deposit_index = deposit_tx.output_index_for_address(refund_hash160)

    # Catch lookup errors when trying to find the deposit
    if deposit_index is None:
        return None
    else:
        return deposit_tx.outputs[deposit_index].value


def get_payment_output_from_tx(payment_tx, public_key):
    """Get payment info from transaction."""
    payment_index = payment_tx.output_index_for_address(public_key.hash160())

    # Catch lookup errors when trying to find the payment
    if payment_index is None:
        return None
    else:
        return payment_tx.outputs[payment_index]


def get_tx_public_keys(transaction):
    """Get the public keys from a multisignature Transaction object."""
    multisig_info = _get_multisig_info(transaction)
    redeem_script = multisig_info['redeem_script']
    pubkeys = redeem_script.extract_multisig_redeem_info()['public_keys']
    res = {
        'customer': PublicKey_t.from_bytes(pubkeys[0]),
        'merchant': PublicKey_t.from_bytes(pubkeys[1]),
    }
    return res

    # TODO fix this
    # Search the transaction for a public key that we own
    for pubkey in pubkeys:
        public_key = PublicKey_t.from_bytes(pubkey)
        # FIXME: less expensive membership check (testnet address check)
        if wallet.get_private_for_public(public_key):
            res['merchant'] = public_key
        else:
            res['customer'] = public_key

    return res


def verify_half_signed_tx(tx_from_user):
    """Verify a half-signed refund is a valid transaction."""
    redeem_script = _get_multisig_info(tx_from_user)['redeem_script']

    # Verify partial signature in refund transaction
    script_pubkey = Script.build_p2sh(redeem_script.hash160())
    if not tx_from_user.verify_partial_multisig(0, script_pubkey):
        raise BadTransactionError('Invalid refund transaction.')

    # TODO
    # Verify customer pubkey is in refund_tx
    # Verify locktime is some amount of time in the future for refund
    # Verify customer pubkey is not ours
    return True


def parse_tx(tx_hex):
    """Parse a customer transaction.

    Args:
        tx_hex (string): the hexadecimal string representation of a bitcoin
            transaction.

    Returns:
        tx (two1.lib.bitcoin.txn.Transaction): a Transaction object that
        contains the inputs and outputs associated with a bitcoin transaction.
        This operation can be reversed using `serialize_tx`.
    """
    transaction = Transaction_t.from_hex(tx_hex)
    return transaction


def serialize_tx(tx):
    """Serialize a Transaction object into a hex string.

    Args:
        tx (two1.lib.bitcoin.txn.Transaction): a Transaction object that
        contains the inputs and outputs associated with a bitcoin transaction.

    Returns:
        tx_hex (string): the hexadecimal string representation of a bitcoin
            transaction. This can be reversed using `parse_tx`.
    """
    return bytes_to_str(bytes(tx))


def sign_half_signed_tx(tx_from_user):
    """Sign a half-signed transaction.

    Args:
        tx_from_user (two1.lib.bitcoin.txn.Transaction): a Transaction object
            that contains a transaction from a customer, whether for a refund
            or general payment, to be signed by the merchant.

    Returns:
        signed_tx (two1.lib.bitcoin.txn.Transaction): a Transaction object that
            contains a transaction that has been signed by both the customer
            and the merchant.
    """
    try:
        # Get the public keys associated with this transaction
        multisig_info = _get_multisig_info(tx_from_user)
        redeem_script = multisig_info['redeem_script']
        public_keys = get_tx_public_keys(tx_from_user)

        # Sign the first (and hopefully only) input in the transaction
        private_key = wallet.get_private_for_public(public_keys['merchant'])
        tx_from_user.sign_input(
            0, Transaction_t.SIG_HASH_ALL, private_key, redeem_script
        )
    except:
        # Catch the case where we can't sign the transaction
        raise NoMerchantPublicKeyError('No merchant public key to sign.')

    # Return a Transaction containing the fully-signed transaction.
    return tx_from_user
