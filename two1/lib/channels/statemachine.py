import codecs
import time
import enum

import two1.lib.bitcoin as bitcoin

from . import wallet


class StateTransitionError(AssertionError):
    """Invalid state transition error."""
    pass


class InsufficientBalanceError(ValueError):
    """Insufficient balance error."""
    pass


class InvalidTransactionError(ValueError):
    """Invalid transaction error."""
    pass


class PaymentChannelState(enum.Enum):
    """Payment Channel State."""
    OPENING = 1
    CONFIRMING_DEPOSIT = 2
    READY = 3
    OUTSTANDING = 4
    CONFIRMING_SPEND = 5
    CLOSED = 6

    def __str__(self):
        """Convert state to human-readable string.

        Returns:
            str: Formatted state

        """
        mapping = {
            PaymentChannelState.OPENING: 'Opening',
            PaymentChannelState.CONFIRMING_DEPOSIT: 'Confirming Deposit',
            PaymentChannelState.READY: 'Ready',
            PaymentChannelState.OUTSTANDING: 'Outstanding',
            PaymentChannelState.CONFIRMING_SPEND: 'Confirming Spend',
            PaymentChannelState.CLOSED: 'Closed'
        }
        return mapping[self]


class PaymentChannelModel:
    """Payment channel state model. This contains the core state of a payment channel."""

    def __init__(self, **kwargs):
        """Create an instance of PaymentChannelModel.

        Returns:
            PaymentChannelModel: Instance of PaymentChannelModel.

        Attributes:
            url (str): Complete payment channel URL (primary key)
            state (PaymentChannelState): State machine state
            creation_time (float): Creation UNIX time
            deposit_tx (bitcoin.Transaction or None): Deposit transaction
            refund_tx (bitcoin.Transaction or None): Refund transaction
            payment_tx (bitcoin.Transaction or None): Payment transaction
            spend_tx (bitcoin.Transaction or None): Spend transaction
            spend_txid (str or None): Spend txid

        """
        self.url = kwargs.get('url', None)
        self.state = kwargs.get('state', PaymentChannelState.OPENING)
        self.creation_time = kwargs.get('creation_time', None)
        self.deposit_tx = kwargs.get('deposit_tx', None)
        self.refund_tx = kwargs.get('refund_tx', None)
        self.payment_tx = kwargs.get('payment_tx', None)
        self.spend_tx = kwargs.get('spend_tx', None)
        self.spend_txid = kwargs.get('spend_txid', None)

    def __repr__(self):
        return "<Channel(url='{}', state='{}', creation_time={}, deposit_tx='{}', refund_tx='{}', payment_tx='{}', spend_tx='{}', spend_txid='{}')>".format(self.url, self.state, self.creation_time, self.deposit_tx, self.refund_tx, self.payment_tx, self.spend_tx, self.spend_txid)


class PaymentChannelStateMachine:
    """Customer payment channel state machine interface."""

    def __init__(self, model, wallet):
        """Instantiate a payment channel state machine.

        Args:
            model (PaymentChannelModel): State model.
            wallet (WalletWrapperBase): Instance of the wallet interface.

        Returns:
            PaymentChannelStateMachine: Instance of PaymentChannelStateMachine.

        """
        self._model = model
        self._wallet = wallet

        # Temporary state (between READY and OUTSTANDING states)
        self._pending_payment_tx = None
        self._pending_amount = None

    def create(self, merchant_public_key, deposit, expiration, fee, zeroconf, use_unconfirmed=False):
        """Open a new payment channel.

        State machine transitions from OPENING to CONFIRMING_DEPOSIT if
        zeroconf is False, and to READY if zeroconf is True.

        Args:
            merchant_public_key (str): Serialized compressed public key of the
                merchant (ASCII hex).
            deposit (int): Depost amount in satoshis.
            expiration (int): Relative expiration time in seconds.
            fee (int): Fee amount in satoshis.
            zeroconf (bool): Use payment channel without deposit confirmation.
            use_unconfirmed (bool): Use unconfirmed transactions to build
                deposit transaction.

        Returns:
            tuple: Serialized half-signed refund transaction (ASCII hex),
                callback that takes serialized fully-signed refund transaction
                (ASCII hex).

        Raises:
            StateTransitionError: If channel is already open.
            TypeError: If merchant_public_key type is not str, deposit type is
                not int, or expiration type is not int.
            ValueError: If relative expiration time, deposit, or fee are
                negative.
            InsufficientBalanceError: If wallet has insufficient balance to
                make deposit for payment channel.

        """
        # Assert state
        if self._model.state != PaymentChannelState.OPENING:
            raise StateTransitionError("Channel state is not Opening.")

        # Validate inputs
        if not isinstance(merchant_public_key, str):
            raise TypeError("Merchant public key type should be str.")
        elif not isinstance(deposit, int):
            raise TypeError("Deposit type should be int.")
        elif not isinstance(expiration, int):
            raise TypeError("Expiration type should be int.")
        elif expiration <= 0:
            raise ValueError("Expiration should be positive.")
        elif deposit <= 0:
            raise ValueError("Deposit should be positive.")
        elif fee <= 0:
            raise ValueError("Fee should be positive.")

        # Setup initial amounts and expiration time
        creation_time = time.time()
        expiration_time = int(creation_time + expiration)

        # Collect public keys
        customer_public_key = self._wallet.get_public_key()
        merchant_public_key = bitcoin.PublicKey.from_bytes(codecs.decode(merchant_public_key, 'hex_codec'))

        # Build redeem script
        public_keys = [customer_public_key.compressed_bytes, merchant_public_key.compressed_bytes]
        redeem_script = bitcoin.Script.build_multisig_redeem(2, public_keys)

        # Build deposit tx
        try:
            deposit_tx = self._wallet.create_deposit_tx(redeem_script.address(), deposit, fee, use_unconfirmed=use_unconfirmed)
        except wallet.InsufficientBalanceError as e:
            raise InsufficientBalanceError(str(e))

        # Build refund tx
        refund_tx = self._wallet.create_refund_tx(deposit_tx, redeem_script, customer_public_key, expiration_time, fee)

        # Update model state
        self._model.creation_time = creation_time
        self._model.deposit_tx = deposit_tx
        self._model.refund_tx = refund_tx

        return (refund_tx.to_hex(), lambda refund_tx: self._create_finish(refund_tx, zeroconf))

    def _create_finish(self, refund_tx, zeroconf):
        # Assert state
        if self._model.state != PaymentChannelState.OPENING:
            raise StateTransitionError("Channel state is not Opening.")

        # Deserialize refund transaction
        refund_tx = bitcoin.Transaction.from_hex(refund_tx)

        # Validate transaction input
        if len(refund_tx.inputs) != 1:
            raise InvalidTransactionError("Invalid refund transaction inputs length.")
        elif str(refund_tx.inputs[0].outpoint) != self.deposit_txid:
            raise InvalidTransactionError("Refund transaction input does not use deposit transction.")

        # Validate transaction output
        if len(refund_tx.outputs) != 1:
            raise InvalidTransactionError("Invalid refund transaction outputs length.")
        # Find output corresponding to our address
        my_hash160 = "0x" + codecs.encode(self._customer_public_key.hash160(), "hex_codec").decode('utf-8')
        my_outputs = list(filter(lambda output: output.script.get_hash160() == my_hash160, refund_tx.outputs))
        if len(my_outputs) != 1:
            raise InvalidTransactionError("Invalid output address in refund transaction.")
        # Validate transaction output value
        if refund_tx.outputs[0].value != self.deposit_amount:
            raise InvalidTransactionError("Invalid output value in refund transaction.")

        # Validate transaction lock time
        if refund_tx.lock_time != self.expiration_time:
            raise InvalidTransactionError("Invalid locktime in refund transaction.")

        # Verify P2SH deposit spend signature
        if not refund_tx.verify_input_signature(0, self._model.deposit_tx.outputs[self.deposit_tx_utxo_index].script):
            raise InvalidTransactionError("Invalid input signature in refund transaction.")

        # Update core state
        self._model.refund_tx = refund_tx
        if not zeroconf:
            self._model.state = PaymentChannelState.CONFIRMING_DEPOSIT
        else:
            self._model.state = PaymentChannelState.READY

    def confirm(self):
        """Confirm the deposit of the payment channel.

        State machine transitions from CONFIRMING_DEPOSIT to READY.

        Raises:
            StateTransitionError: If channel is not in CONFIRMING_DEPOSIT
                state.

        """
        # Assert state
        if self._model.state != PaymentChannelState.CONFIRMING_DEPOSIT:
            raise StateTransitionError("Channel state is not Confirming Deposit.")

        self._model.state = PaymentChannelState.READY

    def pay(self, amount):
        """Create a half-signed payment to the channel.

        State machine state transitions from READY to OUTSTANDING.

        Args:
            amount (int): Amount to pay in satoshis.

        Returns:
            str: Serialized half-signed payment transaction (ASCII hex).

        Raises:
            StateTransitionError: If channel is not in READY state.
            TypeError: If amount type is not int.
            ValueError: if amount is negative or zero.
            InsufficientBalanceError: If payment channel balance is
                insufficient to pay.

        """
        # Assert state
        if self._model.state != PaymentChannelState.READY:
            raise StateTransitionError("Channel not ready.")

        # Validate amount
        if not isinstance(amount, int):
            raise TypeError("Amount type should be int.")
        elif amount < 0:
            raise ValueError("Amount should be positive.")
        elif (self.balance_amount - amount) < 0:
            raise InsufficientBalanceError("Insufficient payment channel balance: requested amount {}, remaining balance {}.".format(amount, self.balance_amount))

        # Build payment tx (FIXME build once and update)
        self._pending_payment_tx = self._wallet.create_payment_tx(self._model.deposit_tx, self._redeem_script, self._merchant_public_key, self._customer_public_key, self.deposit_amount - self.balance_amount + amount, self.fee_amount)
        self._pending_amount = amount

        self._model.state = PaymentChannelState.OUTSTANDING

        return self._pending_payment_tx.to_hex()

    def pay_ack(self):
        """Acknowledge a successful payment to the channel.

        State machine transitions from OUTSTANDING to READY.

        Raises:
            StateTransitionError: If channel is not in OUTSTANDING state.

        """
        # Assert state
        if self._model.state != PaymentChannelState.OUTSTANDING:
            raise StateTransitionError("No payment outstanding.")

        # Make pending payment our last payment and update our balance
        self._model.payment_tx = self._pending_payment_tx

        self._pending_payment_tx = None
        self._pending_amount = None

        self._model.state = PaymentChannelState.READY

    def pay_nack(self):
        """Negative-acknowledge a successful payment to the channel.

        State machine transitions from OUTSTANDING to READY.

        Raises:
            StateTransitionError: If channel is not in OUTSTANDING state.

        """
        # Assert state
        if self._model.state != PaymentChannelState.OUTSTANDING:
            raise StateTransitionError("No payment outstanding.")

        self._pending_payment_tx = None
        self._pending_amount = None

        self._model.state = PaymentChannelState.READY

    def close(self, spend_txid):
        """Close the channel.

        State machine transitions from READY to CONFIRMING_SPEND, OUTSTANDING
        to CONFIRMING_SPEND, OPENING to CONFIRMING_SPEND, or CONFIRMING_SPEND
        to CONFIRMING_SPEND.

        Args:
            spend_txid (str or None): Transaction ID of spending transaction,
                either payment or refund (RPC byte order)

        Raises:
            StateTransitionError: If channel is already closed.

        """
        # Assert state
        if self._model.state == PaymentChannelState.CLOSED:
            raise StateTransitionError("Channel already closed.")

        # If we are still in OPENING, we haven't broadcast a deposit, so go
        # straight to closed.
        if self._model.state == PaymentChannelState.OPENING:
            self._model.state = PaymentChannelState.CLOSED
            return

        self._model.spend_txid = spend_txid
        self._model.state = PaymentChannelState.CONFIRMING_SPEND

    def finalize(self, spend_tx):
        """Finalize the channel. This commits the spending transaction of the
        channel so the final balance can be ascertained.

        State machine transitions from CONFIRMING_SPEND to CLOSED, READY to
        CLOSED, OUTSTANDING to CLOSED, or CLOSED to CLOSED.

        Raises:
            InvalidTransactionError: If spending transaction is invalid.
            StateTranstionError: If channel is not open.

        """
        # Assert state
        if self._model.state == PaymentChannelState.OPENING:
            raise StateTransitionError("Channel not open.")

        # Deserialize spend tx
        spend_tx = bitcoin.Transaction.from_hex(spend_tx)

        # Validate transaction input
        if len(spend_tx.inputs) != 1:
            raise InvalidTransactionError("Invalid spent transaction inputs length.")
        elif str(spend_tx.inputs[0].outpoint) != self.deposit_txid:
            raise InvalidTransactionError("Spent transaction input does not use deposit transction.")

        # Find output corresponding to our address
        my_hash160 = "0x" + codecs.encode(self._customer_public_key.hash160(), "hex_codec").decode('utf-8')
        my_outputs = list(filter(lambda output: output.script.get_hash160() == my_hash160, spend_tx.outputs))
        if len(my_outputs) != 1:
            raise InvalidTransactionError("Invalid spent transaction outputs length.")

        # Verify P2SH deposit spend signature
        if not spend_tx.verify_input_signature(0, self._model.deposit_tx.outputs[self.deposit_tx_utxo_index].script):
            raise InvalidTransactionError("Invalid input signature in spend transaction.")

        # Save spend tx
        self._model.spend_tx = spend_tx
        self._model.spend_txid = str(spend_tx.hash)
        self._model.state = PaymentChannelState.CLOSED

    # Private Properties

    @property
    def _redeem_script(self):
        """Get channel redeem script.

        Returns:
            bitcoin.Script: Redeem script.

        """
        return self._model.refund_tx.inputs[0].script.extract_multisig_sig_info()['redeem_script']

    @property
    def _customer_public_key(self):
        """Get channel customer public key.

        Returns:
            bitcoin.PublicKey: Customer public key.

        """
        return bitcoin.PublicKey.from_bytes(self._redeem_script.extract_multisig_redeem_info()['public_keys'][0])

    @property
    def _merchant_public_key(self):
        """Get channel merchant public key.

        Returns:
            bitcoin.PublicKey: Merchant public key.

        """
        return bitcoin.PublicKey.from_bytes(self._redeem_script.extract_multisig_redeem_info()['public_keys'][1])

    # Public Properties

    @property
    def state(self):
        """Get channel state machine state.

        Returns:
            PaymentChannelState: State machine state.

        """
        return self._model.state

    @property
    def balance_amount(self):
        """Get channel balance amount.

        Returns:
            int: Balance amount in satoshis.

        """
        if self._model.spend_tx:
            output_index = self._model.spend_tx.output_index_for_address(self._customer_public_key.hash160())
            return self._model.spend_tx.outputs[output_index].value
        elif self._model.payment_tx:
            return self.deposit_amount - self._model.payment_tx.outputs[0].value
        else:
            return self.deposit_amount

    @property
    def deposit_amount(self):
        """Get channel deposit amount.

        Returns:
            int: Deposit amount in satoshis.

        """
        return self._model.refund_tx.outputs[0].value

    @property
    def fee_amount(self):
        """Get channel fee amount.

        Returns:
            int: Fee amount in satoshis.

        """
        return self._model.deposit_tx.outputs[self.deposit_tx_utxo_index].value - self._model.refund_tx.outputs[0].value

    @property
    def creation_time(self):
        """Get channel creation time.

        Returns:
            float: Creation absolute time (UNIX time).

        """
        return self._model.creation_time

    @property
    def expiration_time(self):
        """Get channel expiration time.

        Returns:
            int: Expiration absolute time (UNIX time).

        """
        return self._model.refund_tx.lock_time

    @property
    def deposit_tx_utxo_index(self):
        """Get channel deposit transaction P2SH output index.

        Returns:
            int or None: Output index in deposit transaction.

        """
        return self._model.deposit_tx.output_index_for_address(self._redeem_script.hash160()) if self._model.deposit_tx else None

    @property
    def deposit_tx(self):
        """Get channel deposit transaction.

        Returns:
            str or None: Serialized deposit transaction (ASCII hex).

        """
        return self._model.deposit_tx.to_hex() if self._model.deposit_tx else None

    @property
    def deposit_txid(self):
        """Get channel deposit transaction ID.

        Returns:
            str or None: Deposit transaction ID (RPC byte order).

        """
        return str(self._model.deposit_tx.hash) if self._model.deposit_tx else None

    @property
    def deposit_txid_signature(self):
        """Get channel deposit transaction ID signature, to authenticate
        channel close with server.

        Returns:
            str or None: DER-encoded signature (ASCII hex).

        """
        return codecs.encode(self._wallet.sign(self.deposit_txid.encode(), self._customer_public_key).to_der(), 'hex_codec').decode() if self._model.deposit_tx else None

    @property
    def refund_tx(self):
        """Get channel refund transaction.

        Returns:
            str or None: Serialized refund transaction (ASCII hex).

        """
        return self._model.refund_tx.to_hex() if self._model.refund_tx else None

    @property
    def refund_txid(self):
        """Get channel refund transaction ID.

        Returns:
            str or None: Refund transaction ID (RPC byte order).

        """
        return str(self._model.refund_tx.hash) if self._model.refund_tx else None

    @property
    def payment_tx(self):
        """Get channel payment transaction.

        Returns:
            str or None: Serialized payment transaction (ASCII hex).

        """
        return self._model.payment_tx.to_hex() if self._model.payment_tx else None

    @property
    def spend_tx(self):
        """Get channel spend transaction.

        Returns:
            str or None: Serialized spend transaction (ASCII hex).

        """
        return self._model.spend_tx.to_hex() if self._model.spend_tx else None

    @property
    def spend_txid(self):
        """Get channel spend transaction ID.

        Returns:
            str or None: Spend transaction ID (RPC byte order).

        """
        return str(self._model.spend_tx.hash) if self._model.spend_tx else self._model.spend_txid
