"""Tests for payment channel functionality."""

import os
import time
import codecs
from pytz import utc
from datetime import datetime

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

import two1.lib.bitcoin as bitcoin
from .wallet import Two1WalletWrapper, MockTwo1Wallet
from .paymentserver import PaymentServer, PaymentServerError


class PaymentServerUnitTests(TestCase):

    """Test PaymentServer primary methods."""

    TEST_DEPOSIT_AMOUNT = 100000
    cust_wallet = MockTwo1Wallet()
    merch_wallet = MockTwo1Wallet()
    server = PaymentServer(merch_wallet, testnet=True)

    def _create_client_txs(self):
        """Mock client transactions for opening a channel."""
        # Collect public keys
        deposit = self.TEST_DEPOSIT_AMOUNT
        expiration_time = int(time.time() + 86400)
        customer_public_key = self.cust_wallet.get_payout_public_key()
        merchant_public_key = self.merch_wallet.get_payout_public_key()

        # Build redeem script
        pubkeys = [customer_public_key.compressed_bytes,
                   merchant_public_key.compressed_bytes]
        redeem_script = bitcoin.script.Script.build_multisig_redeem(2, pubkeys)

        # Build deposit tx
        deposit_tx = self.cust_wallet.create_deposit_tx(
            redeem_script.hash160())

        # Build refund tx
        refund_tx = self.cust_wallet.create_refund_tx(
            deposit_tx, redeem_script, customer_public_key, expiration_time,
            10000)

        # Build payment tx
        payment_tx = self.cust_wallet.create_payment_tx(
            deposit_tx, redeem_script, merchant_public_key,
            customer_public_key, 5000, 10000)

        return deposit_tx, refund_tx, payment_tx

    def test_discovery(self):
        """Test ability to discover a new payment channel."""
        merchant_public_key = self.server.discovery()
        test_public_key = codecs.encode(
            self.merch_wallet._private_key.public_key.compressed_bytes,
            'hex_codec').decode('utf-8')
        self.assertEqual(merchant_public_key, test_public_key)

    def test_initialize_handshake(self):
        """Test ability to initialize a payment channel handshake."""
        # Create refund transaction using test data utility
        _, refund_tx, _ = self._create_client_txs()

        # Initialize the handshake and ensure that it returns sucessfully
        initialized = self.server.initialize_handshake(refund_tx)
        self.assertTrue(initialized)

        # Test for handshake failure when using the same refund twice
        with self.assertRaises(PaymentServerError):
            initialized = self.server.initialize_handshake(refund_tx)

    def test_complete_handshake(self):
        """Test ability to complete a payment channel handshake."""
        # Create deposit and refund transactions using test data utility
        deposit_tx, refund_tx, _ = self._create_client_txs()
        deposit_txid = str(deposit_tx.hash)

        # Test that handshake completion fails when no channel exists
        with self.assertRaises(PaymentServerError):
            self.server.complete_handshake(deposit_txid, deposit_tx)

        # Test that handshake completion succeeds
        self.server.initialize_handshake(refund_tx)
        completed = self.server.complete_handshake(deposit_txid, deposit_tx)
        self.assertTrue(completed)

        # Test that handshake completion fails with a duplicate deposit
        with self.assertRaises(PaymentServerError):
            self.server.complete_handshake(deposit_txid, deposit_tx)

    def test_receive_payment(self):
        """Test ability to receive a payment within a channel."""
        deposit_tx, refund_tx, payment_tx = self._create_client_txs()
        deposit_txid = str(deposit_tx.hash)

        # Test that payment receipt fails when no channel exists
        with self.assertRaises(PaymentServerError):
            self.server.receive_payment(deposit_txid, payment_tx)

        # Test that payment receipt succeeds
        self.server.initialize_handshake(refund_tx)
        self.server.complete_handshake(deposit_txid, deposit_tx)
        paid = self.server.receive_payment(deposit_txid, payment_tx)
        self.assertTrue(paid)

        # Test that payment receipt fails with a duplicate payment
        with self.assertRaises(PaymentServerError):
            self.server.receive_payment(deposit_txid, payment_tx)

    # TODO
    # def test_redeem_payment(self):
    #     """Test ability to redeem a payment made within a channel."""
    #     self.assertTrue(True)
    #
    # def test_status_close_channel(self):
    #     """Test ability to get a channel's status and close it."""
    #     self.assertTrue(True)
