"""Wrapper around the two1 wallet for payment channels."""
import codecs
import two1.lib.bitcoin as bitcoin
from two1.lib.bitcoin import Script
from two1.lib.bitcoin import Transaction
from two1.lib.bitcoin import PrivateKey, PublicKey


class WalletError(Exception):
    pass


class NoMerchantPublicKeyError(WalletError):
    pass


class TransactionVerificationError(WalletError):
    pass


class InvalidPaymentError(WalletError):
    pass


class WalletWrapperBase:

    def __init__(self):
        pass

    def get_public_key(self):
        raise NotImplementedError()

    def verify_half_signed_tx(self):
        raise NotImplementedError()

    def sign_half_signed_tx(self):
        raise NotImplementedError()


def get_redeem_script(transaction):
    """Get the redeem script from a Transaction object."""
    input_script = transaction.inputs[0].script
    multisig_info = input_script.extract_multisig_sig_info()
    return multisig_info['redeem_script']


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
        pubkey = self._wallet.get_payout_public_key(
            self._account).compressed_bytes
        public_key = codecs.encode(pubkey, 'hex_codec').decode('utf-8')
        return public_key

    def verify_half_signed_tx(self, tx_from_user):
        """Verify a half-signed refund is a valid transaction."""
        redeem_script = get_redeem_script(tx_from_user)

        # Verify partial signature in refund transaction
        script_pubkey = Script.build_p2sh(redeem_script.hash160())
        if not tx_from_user.verify_partial_multisig(0, script_pubkey):
            raise TransactionVerificationError(
                'Half-signed transaction could not be verified.')

        return True

    def sign_half_signed_tx(self, tx_from_user, merch_key):
        """Sign a half-signed transaction.

        Args:
            tx_from_user (two1.lib.bitcoin.txn.Transaction): an object that
                contains a transaction from a customer, whether for a refund
                or general payment, to be signed by the merchant.

            merch_key (two1.lib.bitcoin.crypto.PublicKey): an object that
                contains the merchant's public key associated with the multisig
                transaction in a payment channel.

        Returns:
            signed_tx (two1.lib.bitcoin.txn.Transaction): an object that
                contains a transaction that has been signed by both the
                customer and the merchant.
        """
        try:
            # Get the public keys associated with this transaction
            redeem_script = get_redeem_script(tx_from_user)

            # Verify that the deposit spend has only one input
            if len(tx_from_user.inputs) != 1:
                raise InvalidPaymentError('Transaction should have one input.')

            # Sign the first (and only) input in the transaction
            private_key = self._wallet.get_private_for_public(merch_key)
            tx_from_user.sign_input(
                0, Transaction.SIG_HASH_ALL, private_key, redeem_script)
        except:
            # Catch the case where we can't sign the transaction
            raise NoMerchantPublicKeyError('No merchant public key to sign.')

        # Return a Transaction containing the fully-signed transaction.
        return tx_from_user

    def get_merchant_key_from_keys(self, pubkeys):
        """Return which key from a list of keys belongs to the merchant."""
        for pubkey in pubkeys:
            public_key = PublicKey.from_bytes(pubkey)
            private_key = self._wallet.get_private_for_public(public_key)
            if private_key is not None:
                return public_key

###############################################################################


class MockTwo1Wallet:

    """Wallet to mock two1 wallet functions in a test environment."""

    def __init__(self):
        """Initialize the mock wallet with a private key."""
        self._private_key = PrivateKey.from_random()

    def get_payout_public_key(self, account='default'):
        """Return the public key associated with the private key."""
        return self._private_key.public_key

    def get_private_for_public(self, public_key):
        """Get this private key for this public key."""
        if public_key.to_hex() == self._private_key.public_key.to_hex():
            return self._private_key
        else:
            return None

    def create_deposit_tx(self, hash160):
        """Return a mocked deposit transaction.

        This uses the hex from some transaction I had lying around and then
        modifies the outputs to pay to the multisig script hash. I basically
        just needed some UTXO's to pay for this thing.
        """
        tx_bytes = codecs.decode(
            '010000000295c5ca7c5d339d476456e5798bc5d483c37234adedeea1d6d58bd7'
            '4dcb3ab488000000006b483045022100bdb985c42ff8db57bd936fd2c7567e0b'
            '4220012b568a956c8b1dcfdef049effb0220637c5f5aad734f3fe42f8a5e2879'
            '174d219dcda516a370d8fd9d2a8d97193668012102a00465ffe29a8a3abd021b'
            '8037fb4467c0a734588449694dda8309495de5dc8affffffff1443c6572f221d'
            '02e072b5efd3af62833ade83c681e8c1ed6620a4020c300aac000000006b4830'
            '4502210086414fe8cc24bbcdebc4238201c3d021d4cd0b0a39b69538227fcfd5'
            'cca8df8c0220540cd8d8ab4f7a03a89fb686cec4f4a47f0b4d9d477c383b040b'
            'a1d7f0b5313c01210237c3846c8f7f86c86078344ff0e09c73d48bec4a1e60dd'
            '99df1ddb2816d1196dffffffff02b0ad01000000000017a9147487cdfa3235a3'
            '479dc05a10504bd8127aa0bab08780380100000000001976a914928f936fc8f9'
            '5dc733d64ebef37d7f57ea70813a88ac00000000', 'hex_codec')
        tx = Transaction.from_bytes(tx_bytes)[0]

        # Modify the transaction to use the hash160 of a redeem script
        tx.outputs[0].script = Script.build_p2sh(hash160)
        return tx

    def create_refund_tx(self, deposit_tx, redeem_script, refund_public_key,
                         expiration_time, fee):
        # Find P2SH output index in deposit_tx
        deposit_utxo_index = 0
        # Look up deposit amount
        deposit_amount = deposit_tx.outputs[deposit_utxo_index].value - fee

        # Build unsigned refund transaction
        script_sig = bitcoin.script.Script()
        inputs = [bitcoin.txn.TransactionInput(
            deposit_tx.hash, deposit_utxo_index, script_sig, 0x0)]
        outputs = [bitcoin.txn.TransactionOutput(
            deposit_amount, bitcoin.script.Script.build_p2pkh
            (refund_public_key.hash160()))]
        refund_tx = bitcoin.txn.Transaction(
            1, inputs, outputs, expiration_time)

        # Sign refund transaction
        public_key = bitcoin.crypto.PublicKey.from_bytes(
            redeem_script.extract_multisig_redeem_info()['public_keys'][0])
        private_key = self.get_private_for_public(public_key)
        refund_tx.sign_input(0, bitcoin.txn.Transaction.SIG_HASH_ALL,
                             private_key, redeem_script)

        return refund_tx

    def create_payment_tx(self, deposit_tx, redeem_script, merchant_public_key,
                          customer_public_key, amount, fee):
        # Find P2SH output index in deposit_tx
        deposit_utxo_index = deposit_tx.output_index_for_address(
            redeem_script.hash160())

        # Look up deposit amount
        deposit_amount = deposit_tx.outputs[deposit_utxo_index].value - fee

        # Build unsigned payment transaction
        script_sig = bitcoin.script.Script()
        inputs = [bitcoin.txn.TransactionInput(
            deposit_tx.hash, deposit_utxo_index, script_sig, 0xffffffff)]
        outputs = [bitcoin.txn.TransactionOutput(
            amount, bitcoin.script.Script.build_p2pkh(
                merchant_public_key.hash160())),
            bitcoin.txn.TransactionOutput(
            deposit_amount - amount,
            bitcoin.script.Script.build_p2pkh(customer_public_key.hash160()))]
        payment_tx = bitcoin.txn.Transaction(1, inputs, outputs, 0x0)

        # Sign payment transaction
        public_key = bitcoin.crypto.PublicKey.from_bytes(
            redeem_script.extract_multisig_redeem_info()['public_keys'][0])
        private_key = self.get_private_for_public(public_key)
        payment_tx.sign_input(0, bitcoin.txn.Transaction.SIG_HASH_ALL,
                              private_key, redeem_script)

        return payment_tx
