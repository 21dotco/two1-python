import codecs
import os.path
import requests

import two1.lib.bitcoin as bitcoin
from two1.lib.wallet import Wallet

from . import blockchain
from .statemachine import PaymentChannelRedeemScript


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

    def open(self, deposit_tx, redeem_script):
        """Open a new payment channel with the merchant.

        Args:
            deposit_tx (str): Serialized deposit transaction.
            redeem_script (str): Serialized redeem script.

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

    PROTOCOL_VERSION = 2

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

        channel_info = r.json()

        # Check protocol version before proceeding
        if channel_info['version'] != HTTPPaymentChannelServer.PROTOCOL_VERSION:
            raise PaymentChannelServerError("Unsupported protocol version: Server version is {}, client version is {}.".format(channel_info['version'], HTTPPaymentChannelServer.PROTOCOL_VERSION))

        return channel_info['public_key']

    def open(self, deposit_tx, redeem_script):
        r = requests.post(self._url, data={'deposit_tx': deposit_tx, 'redeem_script': redeem_script})
        if r.status_code != 200:
            raise PaymentChannelServerError("Opening payment channel: Status Code {}, {}".format(r.status_code, r.text))

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
    """Mock Payment Channel Server interface for local testing."""

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
        return codecs.encode(self._wallet.get_payout_public_key().compressed_bytes, 'hex_codec').decode('utf-8')

    def open(self, deposit_tx, redeem_script):
        # Deserialize deposit tx and redeem script
        deposit_tx = bitcoin.Transaction.from_hex(deposit_tx)
        redeem_script = bitcoin.Script.from_hex(redeem_script)

        # FIXME verify

    def pay(self, deposit_txid, payment_tx):
        # Deserialize payment tx and redeem script
        payment_tx = bitcoin.Transaction.from_hex(payment_tx)
        redeem_script = PaymentChannelRedeemScript.from_bytes(payment_tx.inputs[0].script[-1])

        # Sign payment tx
        public_key = redeem_script.merchant_public_key
        private_key = self._wallet.get_private_for_public(public_key)
        assert private_key, "Redeem script public key not found in wallet."
        sig = payment_tx.get_signature_for_input(0, bitcoin.Transaction.SIG_HASH_ALL, private_key, redeem_script)[0]

        # Update input script sig
        payment_tx.inputs[0].script.insert(1, sig.to_der() + bitcoin.utils.pack_compact_int(bitcoin.Transaction.SIG_HASH_ALL))

        # FIXME verify

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
        redeem_script = PaymentChannelRedeemScript.from_bytes(payment_tx.inputs[0].script[-1])

        public_key = redeem_script.customer_public_key
        assert public_key.verify(deposit_txid.encode(), bitcoin.Signature.from_der(deposit_txid_signature)), "Invalid deposit txid signature."

        # Broadcast to blockchain
        bc = blockchain.InsightBlockchain("https://blockexplorer.com" if not self._wallet.testnet else "https://testnet.blockexplorer.com")
        bc.broadcast_tx(payment_tx_hex)

        # Return payment txid
        return str(payment_tx.hash)
