import requests
import codecs
import os.path

import two1.lib.bitcoin as bitcoin
from two1.lib.wallet import Wallet

from . import blockchain


class PaymentChannelServerError(Exception):
    """Base class for PaymentChannelServer errors."""
    pass


class PaymentChannelNotFoundError(PaymentChannelServerError):
    """Payment Channel Not Found error."""
    pass


class PaymentChannelServerBase:
    """Base class for a PaymentChannelServer interface."""

    def __init__(self):
        pass

    def get_public_key(self):
        """Get the public key of the merchant to pay to.

        Returns:
            str: Serialized compressed public key (ASCII hex).

        """
        raise NotImplementedError()

    def open(self, refund_tx):
        """Open a new payment channel with the merchant.

        Args:
            refund_tx (str): Serialized half-signed refund transaction.

        Returns:
            tuple: Tuple of signed serialized refund transaction and callback
                that takes deposit txid and deposit transaction to finish
                opening the payment channel.

        """
        raise NotImplementedError()

    def pay(self, deposit_txid, payment_tx):
        """Pay to a payment channel with the merchant.

        Args:
            deposit_txid (str): Deposit transaction ID identifying the payment
                channel (RPC byte order).
            payment_tx (str): Serialized half-signed payment transaction.


        Returns:
            str: Redeemable token for the payment.

        """
        raise NotImplementedError()

    def status(self, deposit_txid):
        """Get status of payment channel.

        Args:
            deposit_txid (str): Deposit transaction ID identifying the payment
                channel (RPC byte order).

        Returns:
            dict: Dictionary of payment channel properties.

        """
        raise NotImplementedError()

    def close(self, deposit_txid, deposit_txid_signature):
        """Close a payment channel.

        Args:
            deposit_txid (str): Deposit transaction ID identifying the payment
                channel (RPC byte order).
            deposit_txid_signature (str): Signature of deposit transaction ID,
                signed by customer prviate key.

        Returns:
            str: Transaction ID of broadcast payment transaction (RPC byte
                order).

        """
        raise NotImplementedError()


class HTTPPaymentChannelServer(PaymentChannelServerBase):
    """RESTful HTTP Payment Channel Server interface. Protocol documented in
    docs/rest-handshake-402.txt."""

    def __init__(self, url):
        """Instantiate a HTTP Payment Channel Server interface for the
        specified URL.

        Args:
            url (str): URL of HTTP Payment Channel Server.

        Returns:
            HTTPPaymentChannelServer: instance of HTTPPaymentChannelServer.

        """
        super().__init__()
        self._url = url

    def get_public_key(self):
        r = requests.get(self._url)
        if r.status_code != 200:
            raise PaymentChannelServerError("Getting merchant public key: Status Code {}, {}".format(r.status_code, r.text))

        public_key_info = r.json()
        return public_key_info['public_key']

    def open(self, refund_tx):
        r = requests.post(self._url, data={'refund_tx': refund_tx})
        if r.status_code != 200:
            raise PaymentChannelServerError("Signing refund transaction: Status Code {}, {}".format(r.status_code, r.text))

        signed_refund = r.json()
        return (signed_refund['refund_tx'], self._open_finish)

    def _open_finish(self, deposit_txid, deposit_tx):
        r = requests.put(self._url + "/" + deposit_txid, data={'deposit_tx': deposit_tx})
        if r.status_code != 200:
            raise PaymentChannelServerError("Sending deposit transaction: Status Code {}, {}".format(r.status_code, r.text))

    def pay(self, deposit_txid, payment_tx):
        r = requests.put(self._url + "/" + deposit_txid, data={'payment_tx': payment_tx})
        if r.status_code == 404:
            raise PaymentChannelNotFoundError()
        elif r.status_code != 200:
            raise PaymentChannelServerError("Sending payment transaction: Status Code {}, {}".format(r.status_code, r.text))

        payment_tx_info = r.json()
        return payment_tx_info['payment_txid']

    def status(self, deposit_txid):
        r = requests.get(self._url + "/" + deposit_txid)
        if r.status_code != 200:
            raise PaymentChannelServerError("Getting payment channel status: Status Code {}, {}".format(r.status_code, r.text))

        return r.json()

    def close(self, deposit_txid, deposit_txid_signature):
        r = requests.delete(self._url + "/" + deposit_txid, data={'signature': deposit_txid_signature})
        if r.status_code != 200:
            raise PaymentChannelServerError("Closing payment channel: Status Code {}, {}".format(r.status_code, r.text))

        payment_tx_info = r.json()
        return payment_tx_info['payment_txid']


class MockPaymentChannelServer(PaymentChannelServerBase):
    """Mock Payment Channel Server interface for testing."""

    def __init__(self, url, wallet=None):
        """Instantiate a Mock Payment Channel Server interface for the
        specified URL.

        Args:
            url (str): URL of Mock server.
            wallet (two1.lib.wallet.Wallet): Wallet instance.

        Returns:
            MockPaymentChannelServer: instance of MockPaymentChannelServer.

        """
        super().__init__()
        self._wallet = wallet if wallet else Wallet()

    def get_public_key(self):
        return codecs.encode(self._wallet.get_payout_public_key('merchant').compressed_bytes, 'hex_codec').decode('utf-8')

    def open(self, refund_tx):
        # Deserialize refund tx and redeem script
        refund_tx = bitcoin.Transaction.from_hex(refund_tx)
        redeem_script = refund_tx.inputs[0].script.extract_multisig_sig_info()['redeem_script']

        # Verify partial signature in refund transaction
        if not refund_tx.verify_partial_multisig(0, bitcoin.Script.build_p2sh(redeem_script.hash160())):
            raise Exception("Partial verification of refund transaction failed.")

        # Sign refund tx
        public_key = bitcoin.PublicKey.from_bytes(redeem_script.extract_multisig_redeem_info()['public_keys'][1])
        private_key = self._wallet.get_private_for_public(public_key)
        assert private_key, "Redeem script public key not found in wallet."
        refund_tx.sign_input(0, bitcoin.Transaction.SIG_HASH_ALL, private_key, redeem_script)

        # Return serialized refund tx
        return (refund_tx.to_hex(), self._open_finish)

    def _open_finish(self, deposit_txid, deposit_tx):
        pass

    def pay(self, deposit_txid, payment_tx):
        # Deserialize payment tx and redeem script
        payment_tx = bitcoin.Transaction.from_hex(payment_tx)
        redeem_script = payment_tx.inputs[0].script.extract_multisig_sig_info()['redeem_script']

        # Verify partial signature in payment transaction
        if not payment_tx.verify_partial_multisig(0, bitcoin.Script.build_p2sh(redeem_script.hash160())):
            raise Exception("Partial verification of refund transaction failed.")

        # Sign payment tx
        public_key = bitcoin.PublicKey.from_bytes(redeem_script.extract_multisig_redeem_info()['public_keys'][1])
        private_key = self._wallet.get_private_for_public(public_key)
        assert private_key, "Redeem script public key not found in wallet."
        payment_tx.sign_input(0, bitcoin.Transaction.SIG_HASH_ALL, private_key, redeem_script)

        # Write payment tx to file
        with open(deposit_txid + ".server.tx", "w") as f:
            f.write(payment_tx.to_hex())

        # Return payment txid
        return str(payment_tx.hash)

    def status(self, deposit_txid):
        return {}

    def close(self, deposit_txid, deposit_txid_signature):
        # Check if a payment has been made to this chanel
        if not os.path.exists(deposit_txid + ".server.tx"):
            raise Exception("No payment has been made to this channel.")

        # Read last payment tx from file
        with open(deposit_txid + ".server.tx") as f:
            payment_tx_hex = f.read().strip()

        # Verify deposit txid singature
        payment_tx = bitcoin.Transaction.from_hex(payment_tx_hex)
        redeem_script = payment_tx.inputs[0].script.extract_multisig_sig_info()['redeem_script']
        public_key = bitcoin.PublicKey.from_bytes(redeem_script.extract_multisig_redeem_info()['public_keys'][0])
        assert public_key.verify(deposit_txid.encode(), bitcoin.Signature.from_der(deposit_txid_signature)), "Invalid deposit txid signature."

        # Broadcast to blockchain
        bc = blockchain.InsightBlockchain("https://blockexplorer.com" if not self._wallet.testnet else "https://testnet.blockexplorer.com")
        bc.broadcast_tx(payment_tx_hex)

        # Return payment txid
        return str(payment_tx.hash)
