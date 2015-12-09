import time

from . import server
from . import statemachine

from .statemachine import PaymentChannelModel
from .statemachine import PaymentChannelState
from .statemachine import PaymentChannelStateMachine


SupportedProtocols = {
    "http": server.HTTPPaymentChannelServer,
    "mock": server.MockPaymentChannelServer,
}
"""Supported protocols table."""


class PaymentChannelError(Exception):
    """Base class for Payment Channel errors."""
    pass


class NotReadyError(PaymentChannelError):
    """Channel not ready error."""
    pass


class NoPaymentError(PaymentChannelError):
    """No payment to close channel error."""
    pass


class ClosedError(PaymentChannelError):
    """Channel closed error."""
    pass


class InsufficientBalanceError(PaymentChannelError):
    """Insufficient balance error."""
    pass


class UnsupportedProtocolError(PaymentChannelError):
    """Unsupported protocol error."""
    pass


class PaymentChannel:
    """Payment channel."""

    DEPOSIT_REBROADCAST_TIMEOUT = 3600
    """Rebroadcast timeout for the deposit, if it hasn't been confirmed by the
    blockchain."""

    def __init__(self, url, database, wallet, blockchain):
        """Instantiate a payment channel object with the specified url.

        Args:
            url (str): Channel url.
            database (DatabaseBase): Instance of the database interface.
            wallet (WalletWrapperBase): Instance of the wallet interface.
            blockchain (BlockchainBase): Instance of the blockchain interface.

        Returns:
            PaymentChannel: instance of PaymentChannel.

        """
        self._url = url
        self._database = database
        self._wallet = wallet
        self._blockchain = blockchain

    @staticmethod
    def open(database, wallet, blockchain, url, deposit, expiration, fee, zeroconf, use_unconfirmed=False):
        """Open a payment channel at the specified URL.

        Args:
            database (DatabaseBase): Instance of the database interface.
            wallet (WalletWrapperBase): Instance of the wallet interface.
            blockchain (BlockchainBase): Instance of the blockchain interface.
            url (str): Payment channel server URL.
            deposit (int): Deposit amount in satoshis
            expiration (int): Relative expiration time in seconds
            fee (int): Fee in in satoshis
            zeroconf (bool): Use payment channel without deposit confirmation.
            use_unconfirmed (bool): Use unconfirmed transactions to build
                deposit transaction.

        Returns:
            PaymentChannel: instance of PaymentChannel.

        Raises:
            UnsupportedProtocolError: If protocol is not supported.
            InsufficientBalanceError: If wallet has insufficient balance to
                make deposit for payment channel.

        """
        # Look up protocol from URL scheme
        try:
            url_scheme = url.split(":")[0]
            protocol = SupportedProtocols[url_scheme]
        except IndexError:
            raise UnsupportedProtocolError("Protocol {} not supported.".format(url_scheme))

        with database:
            # Create a new database model
            model = PaymentChannelModel()
            # Create state machine
            sm = PaymentChannelStateMachine(model, wallet)

            # Create server instance
            payment_server = protocol(url)

            # Call get_public_key() on server
            pubkey = payment_server.get_public_key()

            # Call create() on state machine
            try:
                (deposit_tx, redeem_script) = sm.create(pubkey, deposit, expiration, fee, zeroconf, use_unconfirmed)
            except statemachine.InsufficientBalanceError as e:
                raise InsufficientBalanceError(str(e))

            # Call open(deposit_tx, redeem_script) on server
            payment_server.open(deposit_tx, redeem_script)

            # Call broadcast(deposit_tx) on blockchain
            blockchain.broadcast_tx(sm.deposit_tx)

            # Form the complete payment channel URL
            model.url = url + ("/" if url[-1] != "/" else "") + sm.deposit_txid

            # Add to the database
            database.create(model)

            return PaymentChannel(model.url, database, wallet, blockchain)

    def pay(self, amount):
        """Pay to the payment channel.

        Args:
            amount (int): Amount to pay in satoshis.

        Returns:
            str: Redeemable token for the payment.

        Raises:
            NotReadyError: If payment channel is not ready for payment.
            InsufficientBalanceError: If payment channel balance is
                insufficient to pay.
            ClosedError: If payment channel is closed or was closed by server.
            PaymentChannelError: If an unknown server error occurred.

        """
        closed = False

        with self._database:
            # Look up database model
            model = self._database.read(self._url)
            # Create state machine
            sm = PaymentChannelStateMachine(model, self._wallet)

            # Assert state machine is in ready state
            if sm.state == PaymentChannelState.CLOSED:
                raise ClosedError("Channel closed.")
            if sm.state != PaymentChannelState.READY:
                raise NotReadyError("Channel not ready.")

            # Create server instance
            protocol = SupportedProtocols[model.url.split(":")[0]]
            payment_server = protocol(model.url[:model.url.rfind("/")])

            # Call pay() on state machine
            try:
                payment_tx = sm.pay(amount)
            except statemachine.InsufficientBalanceError as e:
                raise InsufficientBalanceError(str(e))

            # Call pay() on server
            try:
                payment_txid = payment_server.pay(sm.deposit_txid, payment_tx)
                sm.pay_ack()
            except server.PaymentChannelNotFoundError:
                sm.pay_nack()
                sm.close(None)
                closed = True
            except server.PaymentChannelServerError as e:
                sm.pay_nack()
                raise PaymentChannelError("Server: " + str(e))

            # Update database, if successful payment or channel closed
            self._database.update(model)

        if closed:
            raise ClosedError("Channel closed by server.")

        return payment_txid

    def sync(self):
        """Synchronize the payment channel with the blockchain.

        Update the payment channel in the cases of deposit confirmation or
        deposit spend, and refund the payment channel in the case of channel
        expiration.
        """
        with self._database:
            # Look up database model
            model = self._database.read(self._url)
            # Create state machine
            sm = PaymentChannelStateMachine(model, self._wallet)

            # Skip sync if channel is closed
            if sm.state == PaymentChannelState.CLOSED:
                return

            # Check for deposit confirmation
            if sm.state == PaymentChannelState.CONFIRMING_DEPOSIT:
                if self._blockchain.check_confirmed(sm.deposit_txid):
                    sm.confirm()
                elif (time.time() - sm.creation_time) > PaymentChannel.DEPOSIT_REBROADCAST_TIMEOUT:
                    self._blockchain.broadcast_tx(sm.deposit_tx)

            # Check if channel got closed
            if sm.state in (PaymentChannelState.CONFIRMING_SPEND, PaymentChannelState.READY):
                spend_txid = self._blockchain.lookup_spend_txid(sm.deposit_txid, sm.deposit_tx_utxo_index)
                if spend_txid:
                    sm.close(spend_txid)

                    # If spend transaction got confirmed
                    if self._blockchain.check_confirmed(spend_txid):
                        spend_tx = self._blockchain.lookup_tx(spend_txid)
                        sm.finalize(spend_tx)

            # Check for channel expiration
            if sm.state != PaymentChannelState.CLOSED:
                if time.time() > sm.expiration_time:
                    self._blockchain.broadcast_tx(sm.refund_tx)
                    sm.close(sm.refund_txid)

            # Update database
            self._database.update(model)

    def close(self):
        """Close the payment channel.

        Raises:
            NotReadyError: If payment channel is not ready.
            NoPaymentError: If payment channel has no payments.

        """
        with self._database:
            # Look up database model
            model = self._database.read(self._url)
            # Create state machine
            sm = PaymentChannelStateMachine(model, self._wallet)

            # Assert state machine is in ready state
            if sm.state != PaymentChannelState.READY:
                raise NotReadyError("Channel not ready.")

            # Assert payments have been made to the channel
            if not sm.payment_tx:
                raise NoPaymentError("Channel has no payments.")

            # Call close() on server
            protocol = SupportedProtocols[model.url.split(":")[0]]
            payment_server = protocol(model.url[:model.url.rfind("/")])
            payment_txid = payment_server.close(sm.deposit_txid, sm.deposit_txid_signature)

            # Call close() on state machine
            sm.close(payment_txid)

            # Update database
            self._database.update(model)

    @property
    def url(self):
        """Get payment channel URL.

        Returns:
            str: Payment channel URL.

        """
        return self._url

    @property
    def state(self):
        """Get payment channel state.

        Returns:
            PaymentChannelState: Payment channel state.

        """
        with self._database:
            model = self._database.read(self._url)
            return model.state

    @property
    def ready(self):
        """Get readiness of payment channel.

        Returns:
            bool: True if payment channel is ready for payments, False if it is
                not.

        """
        with self._database:
            model = self._database.read(self._url)
            return model.state == PaymentChannelState.READY

    @property
    def balance(self):
        """Get payment channel balance amount.

        Returns:
            int: Balance amount.

        """
        with self._database:
            model = self._database.read(self._url)
            sm = PaymentChannelStateMachine(model, self._wallet)
            return sm.balance_amount

    @property
    def deposit(self):
        """Get payment channel deposit amount.

        Returns:
            int: Deposit amount.

        """
        with self._database:
            model = self._database.read(self._url)
            sm = PaymentChannelStateMachine(model, self._wallet)
            return sm.deposit_amount

    @property
    def fee(self):
        """Get payment channel fee amount.

        Returns:
            int: Fee amount.

        """
        with self._database:
            model = self._database.read(self._url)
            sm = PaymentChannelStateMachine(model, self._wallet)
            return sm.fee_amount

    @property
    def creation_time(self):
        """Get payment channel creation time.

        Returns:
            float: Creation absolute time (UNIX time).

        """
        with self._database:
            model = self._database.read(self._url)
            return model.creation_time

    @property
    def expiration_time(self):
        """Get payment channel expiration time.

        Returns:
            int: Expiration absolute time (UNIX time).

        """
        with self._database:
            model = self._database.read(self._url)
            sm = PaymentChannelStateMachine(model, self._wallet)
            return sm.expiration_time

    @property
    def expired(self):
        """Get expiration status of payment channel.

        Returns:
            bool: True if payment channel is expired, False if it is not.

        """
        with self._database:
            model = self._database.read(self._url)
            sm = PaymentChannelStateMachine(model, self._wallet)
            return time.time() > sm.expiration_time

    @property
    def deposit_txid(self):
        """Get deposit transaction ID.

        Returns:
            str or None: Deposit transaction ID (RPC byte order).

        """
        with self._database:
            model = self._database.read(self._url)
            sm = PaymentChannelStateMachine(model, self._wallet)
            return sm.deposit_txid

    @property
    def spend_txid(self):
        """Get spend transaction ID.

        Returns:
            str or None: Spend transaction ID (RPC byte order).

        """
        with self._database:
            model = self._database.read(self._url)
            sm = PaymentChannelStateMachine(model, self._wallet)
            return sm.spend_txid
