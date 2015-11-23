import two1.lib.bitcoin as bitcoin


class WalletError(Exception):
    """Base class for Wallet errors."""
    pass


class InsufficientBalanceError(WalletError):
    """Insufficient balance error."""
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

    def create_deposit_tx(self, script_address, amount, fee, use_unconfirmed=False):
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

    def create_refund_tx(self, deposit_tx, redeem_script, customer_public_key, expiration_time, fee):
        """Create a half-signed refund transaction for a payment channel.

        Args:
            deposit_tx (bitcoin.Transaction): Deposit transaction object.
            redeem_script (bitcoin.Script): Redeem script object.
            customer_public_key (bitcoin.PublicKey): Customer public key (to
                return refund to).
            expiration_time (int): Absolute expiration time (UNIX time).
            fee (int): Fee in satoshis.

        Returns:
            bitcoin.Transaction: Half-signed refund transaction object.

        """
        raise NotImplementedError()

    def create_payment_tx(self, deposit_tx, redeem_script, merchant_public_key, customer_public_key, amount, fee):
        """Create a half-signed payment transaction for a payment channel.

        Args:
            deposit_tx (bitcoin.Transacton): Deposit transaction object.
            redeem_script (bitcoin.Script): Redeem script object.
            merchant_public_key (bitcoin.PublicKey): Merchant public key (to pay to).
            customer_public_key (bitcoin.PublicKey): Customer public key (to
                return change to).
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


class Two1WalletWrapper(WalletWrapperBase):
    """Wallet interface to a two1 Wallet."""

    def __init__(self, wallet):
        """Instantiate a wallet wrapper interface with the specified Wallet.

        Args:
            wallet (two1.lib.wallet.Wallet): Wallet instance.

        Returns:
            Two1WalletWrapper: instance of Two1WalletWrapper.

        """
        super().__init__()
        self._wallet = wallet

    def get_public_key(self):
        return self._wallet.get_change_public_key()

    def create_deposit_tx(self, script_address, amount, fee, use_unconfirmed=False):
        # Sign deposit transaction to script address
        return self._wallet.build_signed_transaction({script_address: amount + fee}, fees=fee, use_unconfirmed=use_unconfirmed, insert_into_cache=True)[0]

    def create_refund_tx(self, deposit_tx, redeem_script, customer_public_key, expiration_time, fee):
        # Find P2SH output index in deposit_tx
        deposit_utxo_index = deposit_tx.output_index_for_address(redeem_script.hash160())

        # Look up deposit amount
        deposit_amount = deposit_tx.outputs[deposit_utxo_index].value - fee

        # Build unsigned refund transaction
        script_sig = bitcoin.Script()
        inputs = [bitcoin.TransactionInput(deposit_tx.hash, deposit_utxo_index, script_sig, 0x0)]
        outputs = [bitcoin.TransactionOutput(deposit_amount, bitcoin.Script.build_p2pkh(customer_public_key.hash160()))]
        refund_tx = bitcoin.Transaction(bitcoin.Transaction.DEFAULT_TRANSACTION_VERSION, inputs, outputs, expiration_time)

        # Sign refund transaction
        public_key = bitcoin.PublicKey.from_bytes(redeem_script.extract_multisig_redeem_info()['public_keys'][0])
        private_key = self._wallet.get_private_for_public(public_key)
        assert private_key, "Redeem script public key not found in wallet."
        refund_tx.sign_input(0, bitcoin.Transaction.SIG_HASH_ALL, private_key, redeem_script)

        return refund_tx

    def create_payment_tx(self, deposit_tx, redeem_script, merchant_public_key, customer_public_key, amount, fee):
        # Find P2SH output index in deposit_tx
        deposit_utxo_index = deposit_tx.output_index_for_address(redeem_script.hash160())

        # Look up deposit amount
        deposit_amount = deposit_tx.outputs[deposit_utxo_index].value - fee

        # Build unsigned payment transaction
        script_sig = bitcoin.Script()
        inputs = [bitcoin.TransactionInput(deposit_tx.hash, deposit_utxo_index, script_sig, 0xffffffff)]
        outputs = [bitcoin.TransactionOutput(amount, bitcoin.Script.build_p2pkh(merchant_public_key.hash160())), bitcoin.TransactionOutput(deposit_amount - amount, bitcoin.Script.build_p2pkh(customer_public_key.hash160()))]
        payment_tx = bitcoin.Transaction(bitcoin.Transaction.DEFAULT_TRANSACTION_VERSION, inputs, outputs, 0x0)

        # Sign payment transaction
        public_key = bitcoin.PublicKey.from_bytes(redeem_script.extract_multisig_redeem_info()['public_keys'][0])
        private_key = self._wallet.get_private_for_public(public_key)
        assert private_key, "Redeem script public key not found in wallet."
        payment_tx.sign_input(0, bitcoin.Transaction.SIG_HASH_ALL, private_key, redeem_script)

        return payment_tx

    def sign(self, message, public_key):
        private_key = self._wallet.get_private_for_public(public_key)
        return private_key.sign(message)
