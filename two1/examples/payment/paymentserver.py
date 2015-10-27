"""Tools for Payment Channels."""

import codecs
from pytz import utc
from datetime import datetime
import two1.examples.server.settings as settings

from .utils import PCUtil
from .wallet import Two1WalletWrapper
from .blockchain import InsightBlockchain
from two1.lib.bitcoin.crypto import PublicKey
from two1.lib.bitserv.channel_data import DatabaseSQLite3


WALLET_ACCOUNT = os.environ.get('WALLET_ACCOUNT', 'default')
wallet = settings.TWO1_WALLET


class PaymentChannelError(Exception):
    pass


class InvalidPaymentError(PaymentChannelError):
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
        cust_key, merch_key = PCUtil.get_tx_public_keys(refund_tx)
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
        refund_hash160 = PCUtil.get_redeem_script(refund_tx).hash160()
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
        if (channel.status != Channel.CONFIRMING and
                channel.status != Channel.READY):
            raise ChannelClosedError('Payment channel closed.')

        # Find the payment amount associated with the merchant address
        transaction_output = PCUtil.get_tx_payment_output(
            payment_tx, merchant_pubkey)

        # Verify that the payment has adequate fees
        if transaction_output is None:
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
        self._db.pmt.create(deposit_txid, payment_tx, new_pmt_amt)

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
        self._blockchain.broadcast(channel['payment_tx'])

        # Record the broadcast in the database
        self._db.pc.update_state(deposit_txid, 'closed')

        return str(channel['payment_tx'].hash)

    @staticmethod
    def redeem(payment_txid):
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
        if not payment['is_redeemed']:
            raise RedeemPaymentError('Payment already redeemed.')

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
    pubkey = wallet.get_payout_public_key(WALLET_ACCOUNT).compressed_bytes
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
    # TODO lookup merchant public key in database
    res = {
        'customer': PublicKey_t.from_bytes(pubkeys[0]),
        'merchant': PublicKey_t.from_bytes(pubkeys[1]),
    }
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
