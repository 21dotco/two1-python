"""Wraps the Two1 `Wallet` to provide methods for payment channel management."""
import two1.bitcoin as bitcoin
import two1.wallet as wallet
from two1.bitcoin import Transaction


class WalletError(Exception):
    """Base class for Wallet errors."""
    pass


class InsufficientBalanceError(WalletError):
    """Insufficient balance error."""
    pass


class InvalidPaymentError(WalletError):
    """Transaction provided is incorrect or malformed."""
    pass


class WalletWrapperBase:
    """Base class for a wallet interface."""

    def __init__(self):
        pass

    def get_public_key(self):
        """Get a public key corresponding to a change address.

        Returns:
            bitcoin.PublicKey: Public key object.
        """
        raise NotImplementedError()

    def get_payout_public_key(self):
        """Get a public key corresponding to a payout address.

        Returns:
            bitcoin.PublicKey: Public key object.
        """
        raise NotImplementedError()

    def validate_public_key(self, public_key):
        """Validate that a public key exists in the wallet.

        Args:
            public_key (two1.bitcoin.PublicKey): Public key to test.

        Returns:
            bool: True if wallet owns the public key, False otherwise.
        """
        raise NotImplementedError()

    def create_deposit_tx(
            self, script_address, amount, fee, use_unconfirmed=False):
        """Create a fully-signed deposit transaction for a payment channel.

        Args:
            script_address (str): Script address (base58-encoded).
            amount (int): Amount in satoshis.
            fee (int): Fee in satoshis.
            use_unconfirmed (bool): Use unconfirmed transactions.

        Returns:
            bitcoin.Transaction: Deposit transaction object.

        """
        raise NotImplementedError()

    def create_refund_tx(
            self, deposit_tx, redeem_script, expiration_time, fee):
        """Create a fully-signed refund transaction for a payment channel.

        Args:
            deposit_tx (bitcoin.Transaction): Deposit transaction object.
            redeem_script (statemachine.PaymentChannelRedeemScript): Redeem
                script object.
            expiration_time (int): Absolute expiration time (UNIX time).
            fee (int): Fee in satoshis.

        Returns:
            bitcoin.Transaction: Refund transaction object.
        """
        raise NotImplementedError()

    def create_unsigned_payment_tx(
            self, deposit_tx, redeem_script, amount, fee):
        """Create an unsigned payment transaction for a payment channel.

        Args:
            deposit_tx (bitcoin.Transacton): Deposit transaction object.
            redeem_script (statemachine.PaymentChannelRedeemScript): Redeem
                script object.
            amount (int): Total amount to pay in satoshis.
            fee (int): Fee in satoshis.

        Returns:
            bitcoin.Transaction: Unsigned payment transaction object.
        """
        raise NotImplementedError()

    def create_payment_tx(self, deposit_tx, redeem_script, amount, fee):
        """Create a half-signed payment transaction for a payment channel.

        Args:
            deposit_tx (bitcoin.Transacton): Deposit transaction object.
            redeem_script (statemachine.PaymentChannelRedeemScript): Redeem
                script object.
            amount (int): Total amount to pay in satoshis.
            fee (int): Fee in satoshis.

        Returns:
            bitcoin.Transaction: Half-signed payment transaction object.
        """
        raise NotImplementedError()

    def sign(self, message, public_key):
        """Sign a message with the private key corresponding to the specified
        public key.

        Args:
            message (bytes): Message to sign.
            public_key (bitcoin.PublicKey): Public key of private key to sign
                with.

        Returns:
            bitcoin.Signature: Signature object.
        """
        raise NotImplementedError()

    def sign_half_signed_payment(self, payment_tx, redeem_script):
        """Sign a half-signed payment transaction.

        Args:
            payment_tx (bitcoin.Transaction): Half-signed payment transaction
                object from a customer, whether for a refund or general
                payment, to be signed by the merchant.

        Returns:
            bitcoin.Transaction: Transaction object that has been signed by
                both the customer and the merchant.
        """
        raise NotImplementedError()

    def broadcast_transaction(self, transaction):
        """Broadcast a signed transaction to the bitcoin network.

        Args:
            transaction (str): Hex-encoded signed transaction to be broadcast.
        """
        raise NotImplementedError()


class Two1WalletWrapper(WalletWrapperBase):
    """Wallet interface to a two1 Wallet."""

    DEPOSIT_CACHE_TIMEOUT = 30
    """Number of seconds the deposit should remain in the cache before expiring."""

    def __init__(self, wallet, blockchain):
        """Instantiate a wallet wrapper interface with the specified Wallet.

        Args:
            wallet (two1.wallet.Wallet): Wallet instance.
            blockchain (two1.channels.blockchain.Blockchain): Blockchain
                data provider.

        Returns:
            Two1WalletWrapper: instance of Two1WalletWrapper.
        """
        super().__init__()
        self._wallet = wallet
        self._blockchain = blockchain

    def get_public_key(self):
        return self._wallet.get_change_public_key()

    def get_payout_public_key(self):
        return self._wallet.get_payout_public_key()

    def validate_public_key(self, public_key):
        private_key = self._wallet.get_private_for_public(public_key)
        return private_key is not None

    def create_deposit_tx(
            self, script_address, amount, fee, use_unconfirmed=False):
        # Sign deposit transaction to script address
        try:
            return self._wallet.build_signed_transaction(
                {script_address: amount + fee},
                fees=fee,
                use_unconfirmed=use_unconfirmed,
                insert_into_cache=True,
                expiration=Two1WalletWrapper.DEPOSIT_CACHE_TIMEOUT)[0]
        except wallet.exceptions.WalletBalanceError as e:
            raise InsufficientBalanceError(str(e))

    def create_refund_tx(
            self, deposit_tx, redeem_script, expiration_time, fee):
        # Find P2SH output index in deposit_tx
        deposit_utxo_index = deposit_tx.output_index_for_address(
            redeem_script.hash160())

        # Look up deposit amount
        deposit_amount = deposit_tx.outputs[deposit_utxo_index].value - fee

        # Build unsigned refund transaction
        inputs = [
            bitcoin.TransactionInput(
                deposit_tx.hash,
                deposit_utxo_index,
                bitcoin.Script(),
                0xfffffffe),
        ]

        outputs = [
            bitcoin.TransactionOutput(
                deposit_amount,
                bitcoin.Script.build_p2pkh(
                    redeem_script.customer_public_key.hash160())),
        ]

        refund_tx = bitcoin.Transaction(
            bitcoin.Transaction.DEFAULT_TRANSACTION_VERSION,
            inputs,
            outputs,
            expiration_time)

        # Sign refund transaction
        public_key = redeem_script.customer_public_key
        private_key = self._wallet.get_private_for_public(public_key)
        assert private_key, "Redeem script public key not found in wallet."
        sig = refund_tx.get_signature_for_input(
            0, bitcoin.Transaction.SIG_HASH_ALL, private_key, redeem_script)[0]

        # Update input script sig
        hash_type = bitcoin.utils.pack_compact_int(
            bitcoin.Transaction.SIG_HASH_ALL)
        script_sig = bitcoin.Script(
            [sig.to_der() + hash_type, b"\x00", bytes(redeem_script)])
        refund_tx.inputs[0].script = script_sig

        return refund_tx

    def create_unsigned_payment_tx(
            self, deposit_tx, redeem_script, amount, fee):
        # Find P2SH output index in deposit_tx
        deposit_utxo_index = deposit_tx.output_index_for_address(
            redeem_script.hash160())

        # Look up deposit amount
        deposit_amount = deposit_tx.outputs[deposit_utxo_index].value - fee

        # Build unsigned payment transaction
        inputs = [
            bitcoin.TransactionInput(
                deposit_tx.hash,
                deposit_utxo_index,
                bitcoin.Script(),
                0xffffffff),
        ]

        outputs = [
            bitcoin.TransactionOutput(
                amount,
                bitcoin.Script.build_p2pkh(
                    redeem_script.merchant_public_key.hash160())),
            bitcoin.TransactionOutput(
                deposit_amount - amount,
                bitcoin.Script.build_p2pkh(
                    redeem_script.customer_public_key.hash160())),
        ]

        payment_tx = bitcoin.Transaction(
            bitcoin.Transaction.DEFAULT_TRANSACTION_VERSION,
            inputs,
            outputs,
            0x0)

        return payment_tx

    def create_payment_tx(self, deposit_tx, redeem_script, amount, fee):
        payment_tx = self.create_unsigned_payment_tx(
            deposit_tx, redeem_script, amount, fee)

        # Sign payment transaction
        public_key = redeem_script.customer_public_key
        private_key = self._wallet.get_private_for_public(public_key)
        assert private_key, "Redeem script public key not found in wallet."
        sig = payment_tx.get_signature_for_input(
            0, bitcoin.Transaction.SIG_HASH_ALL, private_key, redeem_script)[0]

        # Update input script sig
        hash_type = bitcoin.utils.pack_compact_int(
            bitcoin.Transaction.SIG_HASH_ALL)
        script_sig = bitcoin.Script(
            [sig.to_der() + hash_type, "OP_1", bytes(redeem_script)])
        payment_tx.inputs[0].script = script_sig

        return payment_tx

    def sign(self, message, public_key):
        private_key = self._wallet.get_private_for_public(public_key)
        return private_key.sign(message)

    def sign_half_signed_payment(self, payment_tx, redeem_script):
        # Verify that the deposit spend has only one input
        if len(payment_tx.inputs) != 1:
            raise InvalidPaymentError('Transaction should have one input.')

        # Get the public and private keys associated with this transaction
        merchant_public_key = redeem_script.merchant_public_key
        private_key = self._wallet.get_private_for_public(merchant_public_key)

        # Sign the first (and only) input in the transaction
        sig = payment_tx.get_signature_for_input(
            0, Transaction.SIG_HASH_ALL, private_key, redeem_script)[0]

        # Update input script sig
        hash_type = bitcoin.utils.pack_compact_int(
            bitcoin.Transaction.SIG_HASH_ALL)
        payment_tx.inputs[0].script.insert(1, sig.to_der() + hash_type)

        return payment_tx

    def broadcast_transaction(self, transaction):
        # Verify that transaction has not already been broadcast
        txid = str(bitcoin.Transaction.from_hex(transaction).hash)
        if not self._blockchain.lookup_tx(txid):
            self._wallet.broadcast_transaction(transaction)
