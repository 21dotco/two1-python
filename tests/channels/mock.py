import codecs
import two1.bitcoin as bitcoin
import two1.bitcoin.utils as utils

import two1.channels.server as server
import two1.channels.blockchain as blockchain
import two1.channels.statemachine as statemachine


class MockTwo1Wallet:
    """Mock Two1 Wallet interface for unit testing. See two1.wallet.Two1Wallet for API."""

    PRIVATE_KEY = bitcoin.PrivateKey.from_bytes(
        codecs.decode("83407377a24a5cef75dedb0445d2da3a5389ed34c0f0c57266b1ed0a5ebb30c1", 'hex_codec'))

    "Customer private key."

    MOCK_UTXO_SCRIPT_PUBKEY = bitcoin.Script.build_p2pkh(PRIVATE_KEY.public_key.hash160())
    MOCK_UTXO = bitcoin.Hash("3d3834fb69654cea89f9b086642b867c4cb9c86cc0a4cc1972924370dd54de19")
    MOCK_UTXO_INDEX = 1
    "Mock utxo to make deposit transaction."

    def get_change_public_key(self):
        return self.PRIVATE_KEY.public_key

    def build_signed_transaction(
            self, addresses_and_amounts, use_unconfirmed=False, insert_into_cache=False, fees=None, expiration=0):
        address = list(addresses_and_amounts.keys())[0]
        amount = addresses_and_amounts[address]

        inputs = [bitcoin.TransactionInput(self.MOCK_UTXO, self.MOCK_UTXO_INDEX, bitcoin.Script(), 0xffffffff)]
        outputs = [bitcoin.TransactionOutput(amount, bitcoin.Script.build_p2sh(utils.address_to_key_hash(address)[1]))]
        tx = bitcoin.Transaction(bitcoin.Transaction.DEFAULT_TRANSACTION_VERSION, inputs, outputs, 0x0)
        tx.sign_input(0, bitcoin.Transaction.SIG_HASH_ALL, self.PRIVATE_KEY, self.MOCK_UTXO_SCRIPT_PUBKEY)

        return [tx]

    def get_private_for_public(self, public_key):
        assert bytes(public_key) == bytes(self.PRIVATE_KEY.public_key)
        return self.PRIVATE_KEY

    def broadcast_transaction(self, transaction):
        return MockBlockchain.broadcast_tx(MockBlockchain, transaction)

    @property
    def testnet(self):
        return False


class MockPaymentChannelServer(server.PaymentChannelServerBase):
    """Mock Payment Channel Server interface for unit testing."""

    PRIVATE_KEY = bitcoin.PrivateKey.from_bytes(
        codecs.decode("9d1ad8f765996474ff478ef65692a95dba0af2e24cd9e2cb6dfeee52ce2d38e8", 'hex_codec'))
    "Merchant private key."

    blockchain = None
    "Merchant blockchain interface."

    channels = {}
    "Retained server-side channels state across instantiations of this payment channel server \"client\"."

    def __init__(self, url=None):
        """Instantiate a Mock Payment Channel Server interface for the
        specified URL.

        Args:
            url (str): URL of Mock server.

        Returns:
            MockPaymentChannelServer: instance of MockPaymentChannelServer.

        """
        super().__init__()
        self._url = url

    def get_info(self):
        return {'public_key': codecs.encode(self.PRIVATE_KEY.public_key.compressed_bytes, 'hex_codec').decode('utf-8')}

    def open(self, deposit_tx, redeem_script):
        # Deserialize deposit tx and redeem script
        deposit_tx = bitcoin.Transaction.from_hex(deposit_tx)
        deposit_txid = str(deposit_tx.hash)
        redeem_script = statemachine.PaymentChannelRedeemScript.from_bytes(codecs.decode(redeem_script, 'hex_codec'))

        # Validate redeem_script
        assert redeem_script.merchant_public_key.compressed_bytes == self.PRIVATE_KEY.public_key.compressed_bytes

        # Validate deposit tx
        assert len(deposit_tx.outputs) == 1, "Invalid deposit tx outputs."
        output_index = deposit_tx.output_index_for_address(redeem_script.hash160())
        assert output_index is not None, "Missing deposit tx P2SH output."
        assert deposit_tx.outputs[output_index].script.is_p2sh(), "Invalid deposit tx output P2SH script."
        assert deposit_tx.outputs[output_index].script.get_hash160() == redeem_script.hash160(), "Invalid deposit tx output script P2SH address."  # nopep8

        self.channels[deposit_txid] = {'deposit_tx': deposit_tx, 'redeem_script': redeem_script, 'payment_tx': None}

    def pay(self, deposit_txid, payment_tx):
        # Deserialize payment tx
        payment_tx = bitcoin.Transaction.from_hex(payment_tx)

        # Validate payment tx
        redeem_script = self.channels[deposit_txid]['redeem_script']
        assert len(payment_tx.inputs) == 1, "Invalid payment tx inputs."
        assert len(payment_tx.outputs) == 2, "Invalid payment tx outputs."
        assert bytes(payment_tx.inputs[0].script[-1]) == bytes(self.channels[deposit_txid]['redeem_script']), "Invalid payment tx redeem script."  # nopep8

        # Validate payment is greater than the last one
        if self.channels[deposit_txid]['payment_tx']:
            output_index = payment_tx.output_index_for_address(self.PRIVATE_KEY.public_key.hash160())
            assert output_index is not None, "Invalid payment tx output."
            assert payment_tx.outputs[output_index].value > self.channels[deposit_txid]['payment_tx'].outputs[output_index].value, "Invalid payment tx output value."  # nopep8

        # Sign payment tx
        assert redeem_script.merchant_public_key.compressed_bytes == self.PRIVATE_KEY.public_key.compressed_bytes, "Public key mismatch."  # nopep8
        sig = payment_tx.get_signature_for_input(0, bitcoin.Transaction.SIG_HASH_ALL, self.PRIVATE_KEY, redeem_script)[0]  # nopep8

        # Update input script sig
        payment_tx.inputs[0].script.insert(1, sig.to_der() + bitcoin.utils.pack_compact_int(bitcoin.Transaction.SIG_HASH_ALL))  # nopep8

        # Verify signature
        output_index = self.channels[deposit_txid]['deposit_tx'].output_index_for_address(redeem_script.hash160())
        assert payment_tx.verify_input_signature(0, self.channels[deposit_txid]['deposit_tx'].outputs[output_index].script), "Payment tx input script verification failed."  # nopep8

        # Save payment tx
        self.channels[deposit_txid]['payment_tx'] = payment_tx

        # Return payment txid
        return str(payment_tx.hash)

    def status(self, deposit_txid):
        return {}

    def close(self, deposit_txid, deposit_txid_signature):
        # Assert a payment has been made to this chanel
        assert self.channels[deposit_txid]['payment_tx'], "No payment tx exists."

        # Verify deposit txid singature
        public_key = self.channels[deposit_txid]['redeem_script'].customer_public_key
        assert public_key.verify(deposit_txid.encode(), bitcoin.Signature.from_der(deposit_txid_signature)), "Invalid deposit txid signature."  # nopep8

        # Broadcast to blockchain
        self.blockchain.broadcast_tx(self.channels[deposit_txid]['payment_tx'].to_hex())

        # Return payment txid
        return str(self.channels[deposit_txid]['payment_tx'].hash)


class MockBlockchain(blockchain.BlockchainBase):
    """Mock Blockchain interface for unit testing."""

    _blockchain = {}
    """Global blockchain state accessible by other mock objects."""

    def __init__(self):
        """Instantiate a Mock blockchain interface.

        Returns:
            MockBlockchain: instance of MockBlockchain.

        """
        # Reset blockchain state
        for key in list(MockBlockchain._blockchain.keys()):
            del MockBlockchain._blockchain[key]
        # Stores transactions as
        #   {
        #       "<txid>": {
        #                   "tx": <serialized tx>,
        #                   "confirmations": <number of confirmations>,
        #                   "outputs_spent": [
        #                       "<txid>" or None,
        #                       ...
        #                   ]
        #                 },
        #       ...
        #   }

    def mock_confirm(self, txid, num_confirmations=1):
        self._blockchain[txid]['confirmations'] = num_confirmations

    def check_confirmed(self, txid, num_confirmations=1):
        if txid not in self._blockchain:
            return False

        return self._blockchain[txid]['confirmations'] >= num_confirmations

    def lookup_spend_txid(self, txid, output_index):
        if txid not in self._blockchain:
            return None

        if output_index >= len(self._blockchain[txid]['outputs_spent']):
            raise IndexError('Output index out of bounds.')

        return self._blockchain[txid]['outputs_spent'][output_index]

    def lookup_tx(self, txid):
        if txid not in self._blockchain:
            return None

        return self._blockchain[txid]['tx']

    def broadcast_tx(self, tx):
        txobj = bitcoin.Transaction.from_hex(tx)
        txid = str(txobj.hash)

        if txid in self._blockchain:
            return txid

        self._blockchain[txid] = {"tx": tx, "confirmations": 0, "outputs_spent": [None] * len(txobj.outputs)}

        # Mark spent outputs in other blockchain transactions
        for other_txid in self._blockchain:
            for txinput in txobj.inputs:
                if str(txinput.outpoint) == other_txid:
                    self._blockchain[other_txid]['outputs_spent'][txinput.outpoint_index] = txid
