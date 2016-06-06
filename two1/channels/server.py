"""Interfaces with a payment channel server over `http` and `mock` protocols."""
import codecs
import os.path
import requests
import json
import functools

import two1.bitcoin as bitcoin
from two1.wallet import Wallet

from .statemachine import PaymentChannelRedeemScript


class PaymentChannelServerError(Exception):
    """Base class for PaymentChannelServer errors."""
    pass


class PaymentChannelNotFoundError(PaymentChannelServerError):
    """Payment Channel Not Found error."""
    pass


class PaymentChannelConnectionError(PaymentChannelServerError):
    """Payment Channel Connection Error"""
    pass


class PaymentChannelServerBase:
    """Base class for a PaymentChannelServer interface."""

    def __init__(self):
        pass

    def get_info(self):
        """Get the public information of the merchant.

        Returns:
            dict: Dictionary of merchant information
             -public_key: Serialized compressed public key (ASCII hex).
             -zeroconf: Whether the server supports zero-confirmation deposit transactions.

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


class RequestsWrapper(object):
    """Wrapper to use `requests` and deliberately handle errors."""

    def __init__(self):
        pass

    def __getattr__(self, method):
        request = getattr(requests, method)

        @functools.wraps(request)
        def _requests(*args, **kwargs):
            try:
                response = request(*args, **kwargs)
            except requests.exceptions.ConnectionError as e:
                raise PaymentChannelConnectionError(
                    "Connecting to payment channel server: {}".format(e.request.url)) from None
            return response
        return _requests


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
        self._requests = RequestsWrapper()

    def get_info(self):
        r = self._requests.get(self._url)
        if r.status_code != 200:
            raise PaymentChannelServerError(
                "Getting merchant public key: Status Code {}, {}".format(r.status_code, r.text))

        channel_info = r.json()

        # Check protocol version before proceeding
        if channel_info['version'] != HTTPPaymentChannelServer.PROTOCOL_VERSION:
            raise PaymentChannelServerError(
                "Unsupported protocol version: Server version is {}, client version is {}.".format(
                    channel_info['version'], HTTPPaymentChannelServer.PROTOCOL_VERSION))

        return channel_info

    def open(self, deposit_tx, redeem_script):
        r = self._requests.post(self._url, data={'deposit_tx': deposit_tx, 'redeem_script': redeem_script})
        if r.status_code != 200:
            raise PaymentChannelServerError("Opening payment channel: Status Code {}, {}".format(r.status_code, r.text))

    def pay(self, deposit_txid, payment_tx):
        r = self._requests.put(self._url + "/" + deposit_txid, data={'payment_tx': payment_tx})
        if r.status_code == 404:
            raise PaymentChannelNotFoundError()
        elif r.status_code != 200:
            raise PaymentChannelServerError(
                "Sending payment transaction: Status Code {}, {}".format(r.status_code, r.text))

        payment_tx_info = r.json()
        return payment_tx_info['payment_txid']

    def status(self, deposit_txid):
        r = self._requests.get(self._url + "/" + deposit_txid)
        if r.status_code != 200:
            raise PaymentChannelServerError(
                "Getting payment channel status: Status Code {}, {}".format(r.status_code, r.text))

        return r.json()

    def close(self, deposit_txid, deposit_txid_signature):
        r = self._requests.delete(self._url + "/" + deposit_txid, data={'signature': deposit_txid_signature})
        if r.status_code != 200:
            raise PaymentChannelServerError("Closing payment channel: Status Code {}, {}".format(r.status_code, r.text))

        payment_tx_info = r.json()
        return payment_tx_info['payment_txid']


class TestPaymentChannelServer(PaymentChannelServerBase):
    """Test Payment Channel Server interface for local testing."""

    def __init__(self, url, wallet=None):
        """Instantiate a Test Payment Channel Server interface for the
        specified URL.

        Args:
            url (str): URL of Test server.
            wallet (two1.wallet.Wallet): Wallet instance.

        Returns:
            TestPaymentChannelServer: instance of TestPaymentChannelServer.

        """
        super().__init__()
        self._wallet = wallet if wallet else Wallet()

    def _load_channel(self, deposit_txid):
        # Check if a payment has been made to this chanel
        if not os.path.exists(deposit_txid + ".server.tx"):
            raise PaymentChannelNotFoundError("Payment channel not found.")

        # Load JSON channel
        with open(deposit_txid + ".server.tx") as f:
            channel_json = json.load(f)

        # Deserialize into objects
        channel = {}
        channel['deposit_tx'] = bitcoin.Transaction.from_hex(channel_json['deposit_tx'])
        channel['redeem_script'] = PaymentChannelRedeemScript.from_bytes(
            codecs.decode(channel_json['redeem_script'], 'hex_codec'))
        channel['payment_tx'] = bitcoin.Transaction.from_hex(
            channel_json['payment_tx']) if channel_json['payment_tx'] else None
        return channel

    def _store_channel(self, deposit_txid, channel):
        # Form JSON-serializable channel
        channel_json = {}
        channel_json['deposit_tx'] = channel['deposit_tx'].to_hex()
        channel_json['redeem_script'] = channel['redeem_script'].to_hex()
        channel_json['payment_tx'] = channel['payment_tx'].to_hex() if channel['payment_tx'] else None

        # Store JSON channel
        with open(deposit_txid + ".server.tx", "w") as f:
            json.dump(channel_json, f)

    def get_info(self):
        return {'public_key': codecs.encode(self._wallet.get_payout_public_key().compressed_bytes,
                'hex_codec').decode('utf-8'), 'zeroconf': True}

    def open(self, deposit_tx, redeem_script):
        # Deserialize deposit tx and redeem script
        deposit_tx = bitcoin.Transaction.from_hex(deposit_tx)
        try:
            redeem_script = PaymentChannelRedeemScript.from_bytes(codecs.decode(redeem_script, 'hex_codec'))
        except ValueError:
            raise AssertionError("Invalid payment channel redeem script.")

        # Validate deposit tx
        assert len(deposit_tx.outputs) > 1, "Invalid deposit tx outputs."
        output_index = deposit_tx.output_index_for_address(redeem_script.hash160())
        assert output_index is not None, "Missing deposit tx P2SH output."
        assert deposit_tx.outputs[output_index].script.is_p2sh(), "Invalid deposit tx output P2SH script."
        assert deposit_tx.outputs[output_index].script.get_hash160() == redeem_script.hash160(), "Invalid deposit tx output script P2SH address."  # nopep8

        # Store channel
        deposit_txid = str(deposit_tx.hash)
        self._store_channel(
            deposit_txid, {'deposit_tx': deposit_tx, 'redeem_script': redeem_script, 'payment_tx': None})

    def pay(self, deposit_txid, payment_tx):
        # Load channel
        channel = self._load_channel(deposit_txid)

        # Deserialize payment tx and redeem script
        payment_tx = bitcoin.Transaction.from_hex(payment_tx)

        # Validate payment tx
        redeem_script = channel['redeem_script']
        assert len(payment_tx.inputs) == 1, "Invalid payment tx inputs."
        assert len(payment_tx.outputs) == 2, "Invalid payment tx outputs."
        assert bytes(redeem_script) == bytes(channel['redeem_script']), "Invalid payment tx redeem script."
        assert bytes(payment_tx.inputs[0].script[-1]) == bytes(redeem_script), "Invalid payment tx redeem script."

        # Validate payment is greater than the last one
        if channel['payment_tx']:
            output_index = payment_tx.output_index_for_address(redeem_script.merchant_public_key.hash160())
            assert output_index is not None, "Invalid payment tx output."
            assert payment_tx.outputs[output_index].value > channel['payment_tx'].outputs[output_index].value, "Invalid payment tx output value."  # nopep8

        # Sign payment tx
        public_key = redeem_script.merchant_public_key
        private_key = self._wallet.get_private_for_public(public_key)
        assert private_key, "Redeem script public key not found in wallet."
        sig = payment_tx.get_signature_for_input(0, bitcoin.Transaction.SIG_HASH_ALL, private_key, redeem_script)[0]

        # Update input script sig
        payment_tx.inputs[0].script.insert(1, sig.to_der() + bitcoin.utils.pack_compact_int(
            bitcoin.Transaction.SIG_HASH_ALL))

        # Verify signature
        output_index = channel['deposit_tx'].output_index_for_address(redeem_script.hash160())
        assert payment_tx.verify_input_signature(
            0, channel['deposit_tx'].outputs[output_index].script), "Payment tx input script verification failed."

        # Save payment tx
        channel['payment_tx'] = payment_tx
        self._store_channel(deposit_txid, channel)

        # Return payment txid
        return str(payment_tx.hash)

    def status(self, deposit_txid):
        return {}

    def close(self, deposit_txid, deposit_txid_signature):
        # Load channel
        channel = self._load_channel(deposit_txid)

        # Check if a payment has been made to this chanel
        if channel['payment_tx'] is None:
            raise Exception("No payment has been made to this channel.")

        # Verify deposit txid singature
        public_key = channel['redeem_script'].customer_public_key
        assert public_key.verify(
            deposit_txid.encode(), bitcoin.Signature.from_der(deposit_txid_signature)
        ), "Invalid deposit txid signature."

        # Return payment txid
        return str(channel['payment_tx'].hash)
