"""Manages state transitions for PaymentChannel objects."""
import codecs
import time
import enum
import math

import two1.bitcoin as bitcoin
from . import walletwrapper


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
        self.min_output_amount = kwargs.get('min_output_amount', None)

    def __repr__(self):
        return "<Channel(url='{}', state='{}', creation_time={}, deposit_tx='{}', refund_tx='{}', payment_tx='{}', spend_tx='{}', spend_txid='{}', min_output_amount={})>".format(self.url, self.state, self.creation_time, self.deposit_tx, self.refund_tx, self.payment_tx, self.spend_tx, self.spend_txid, self.min_output_amount)  # nopep8


class PaymentChannelRedeemScript(bitcoin.Script):
    """Derived class of Script to create and access the payment channel redeem
    script."""

    def __init__(self, merchant_public_key, customer_public_key, expiration_time):
        """Instantiate a payment channel redeem script.

        Args:
            merchant_public_key (bitcoin.PublicKey): Merchant public key.
            customer_public_key (bitcoin.PublicKey): Customer public key.
            expiration_time (int): Expiration absolute time (UNIX time).

        Returns:
            PaymentChannelRedeemScript: Instance of PaymentChannelRedeemScript.

        """
        super().__init__(["OP_IF", merchant_public_key.compressed_bytes, "OP_CHECKSIGVERIFY", "OP_ELSE", expiration_time.to_bytes(math.ceil(expiration_time.bit_length() / 8), 'little'), "OP_CHECKLOCKTIMEVERIFY", "OP_DROP", "OP_ENDIF", customer_public_key.compressed_bytes, "OP_CHECKSIG"])  # nopep8

    @classmethod
    def from_bytes(cls, b):
        """Instantiate a payment channel redeem script from bytes.

        Args:
            b (bytes): Serialized payment channel redeem script.

        Returns:
            PaymentChannelRedeemScript: Instance of PaymentChannelRedeemScript.

        """
        self = cls.__new__(cls)
        bitcoin.Script.__init__(self, b)

        if not bitcoin.Script.validate_template(self, ["OP_IF", bytes, "OP_CHECKSIGVERIFY", "OP_ELSE", bytes, "OP_CHECKLOCKTIMEVERIFY", "OP_DROP", "OP_ENDIF", bytes, "OP_CHECKSIG"]):  # nopep8
            raise ValueError("Invalid payment channel redeem script.")

        return self

    @property
    def merchant_public_key(self):
        """Get channel merchant public key.

        Returns:
            bitcoin.PublicKey: merchant public key.

        """
        return bitcoin.PublicKey.from_bytes(self[1])

    @property
    def customer_public_key(self):
        """Get channel customer public key.

        Returns:
            bitcoin.PublicKey: Customer public key.

        """
        return bitcoin.PublicKey.from_bytes(self[-2])

    @property
    def expiration_time(self):
        """Get channel expiration time.

        Returns:
            int: Expiration absolute time (UNIX time).

        """
        return int.from_bytes(self[4], 'little')


class PaymentChannelStateMachine:
    """Customer payment channel state machine interface."""

    PAYMENT_TX_MIN_OUTPUT_AMOUNT = 3000
    """Minimum payment transaction output (above dust limit)."""

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

    def create(self, merchant_public_key, deposit_amount, expiration_time, fee_amount, zeroconf, use_unconfirmed=False):
        """Open a new payment channel.

        State machine transitions from OPENING to CONFIRMING_DEPOSIT if
        zeroconf is False, and to READY if zeroconf is True.

        Args:
            merchant_public_key (str): Serialized compressed public key of the
                merchant (ASCII hex).
            deposit_amount (int): Depost amount in satoshis.
            expiration_time (int): Expiration absolute time (UNIX time).
            fee_amount (int): Fee amount in satoshis.
            zeroconf (bool): Use payment channel without deposit confirmation.
            use_unconfirmed (bool): Use unconfirmed transactions to build
                deposit transaction.

        Returns:
            tuple:
                Serialized deposit transaction (ASCII hex), and serialized
                redeem script (ASCII hex).

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
        elif not isinstance(deposit_amount, int):
            raise TypeError("Deposit amount type should be int.")
        elif not isinstance(fee_amount, int):
            raise TypeError("Fee amount type should be int.")
        elif not isinstance(expiration_time, int):
            raise TypeError("Expiration time type should be int.")
        elif expiration_time <= 0:
            raise ValueError("Expiration time should be positive.")
        elif deposit_amount <= 0:
            raise ValueError("Deposit amount should be positive.")
        elif fee_amount <= 0:
            raise ValueError("Fee amount should be positive.")

        # Setup initial amounts and expiration time
        creation_time = time.time()

        # Collect public keys
        customer_public_key = self._wallet.get_public_key()
        merchant_public_key = bitcoin.PublicKey.from_bytes(codecs.decode(merchant_public_key, 'hex_codec'))

        # Build redeem script
        redeem_script = PaymentChannelRedeemScript(merchant_public_key, customer_public_key, expiration_time)

        # Build deposit tx
        try:
            deposit_tx = self._wallet.create_deposit_tx(redeem_script.address(), deposit_amount + PaymentChannelStateMachine.PAYMENT_TX_MIN_OUTPUT_AMOUNT, fee_amount, use_unconfirmed=use_unconfirmed)  # nopep8
        except walletwrapper.InsufficientBalanceError as e:
            raise InsufficientBalanceError(str(e))

        # Build refund tx
        refund_tx = self._wallet.create_refund_tx(deposit_tx, redeem_script, expiration_time, fee_amount)

        # Update model state
        self._model.creation_time = creation_time
        self._model.deposit_tx = deposit_tx
        self._model.refund_tx = refund_tx
        self._model.min_output_amount = PaymentChannelStateMachine.PAYMENT_TX_MIN_OUTPUT_AMOUNT
        if not zeroconf:
            self._model.state = PaymentChannelState.CONFIRMING_DEPOSIT
        else:
            self._model.state = PaymentChannelState.READY

        return (deposit_tx.to_hex(), redeem_script.to_hex())

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
            raise InsufficientBalanceError(
                "Insufficient payment channel balance: requested amount {}, remaining balance {}.".format(
                    amount, self.balance_amount))

        # If this is the first payment, ensure the payment is at least the dust
        # limit
        if not self._model.payment_tx:
            amount = max(self._model.min_output_amount, amount)

        # Build payment tx
        self._pending_payment_tx = self._wallet.create_payment_tx(
            self._model.deposit_tx, self._redeem_script, self.deposit_amount - self.balance_amount + amount,
            self.fee_amount)
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
        to CONFIRMING_SPEND, CONFIRMING_DEPOSIT to CONFIRMING_SPEND, or
        CONFIRMING_SPEND to CONFIRMING_SPEND.

        Args:
            spend_txid (str or None): Transaction ID of spending transaction,
                either payment or refund (RPC byte order)

        Raises:
            StateTransitionError: If channel is already closed.

        """
        # Assert state
        if self._model.state == PaymentChannelState.CLOSED:
            raise StateTransitionError("Channel already closed.")
        if self._model.state == PaymentChannelState.OPENING:
            raise StateTransitionError("Channel not open.")

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
        my_outputs = list(filter(
            lambda output: output.script.get_hash160() == self._customer_public_key.hash160(),
            spend_tx.outputs))
        if len(my_outputs) != 1:
            raise InvalidTransactionError("Invalid spent transaction outputs.")

        # Verify P2SH deposit spend signature
        if not spend_tx.verify_input_signature(0, self._model.deposit_tx.outputs[self.deposit_tx_utxo_index].script):
            raise InvalidTransactionError("Invalid scriptSig in spend transaction.")

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
        return PaymentChannelRedeemScript.from_bytes(self._model.refund_tx.inputs[0].script[-1])

    @property
    def _customer_public_key(self):
        """Get channel customer public key.

        Returns:
            bitcoin.PublicKey: Customer public key.

        """
        return self._redeem_script.customer_public_key

    @property
    def _merchant_public_key(self):
        """Get channel merchant public key.

        Returns:
            bitcoin.PublicKey: Merchant public key.

        """
        return self._redeem_script.merchant_public_key

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
            return self._model.spend_tx.outputs[output_index].value - self._model.min_output_amount
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
        return (self._model.refund_tx.outputs[0].value - self._model.min_output_amount) if self._model.refund_tx else None  # nopep8

    @property
    def fee_amount(self):
        """Get channel fee amount.

        Returns:
            int: Fee amount in satoshis.

        """
        return (self._model.deposit_tx.outputs[self.deposit_tx_utxo_index].value - self._model.refund_tx.outputs[0].value) if self._model.refund_tx else None  # nopep8

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
        return self._model.refund_tx.lock_time if self._model.refund_tx else None

    @property
    def deposit_tx_utxo_index(self):
        """Get channel deposit transaction P2SH output index.

        Returns:
            int or None: Output index in deposit transaction.

        """
        return self._model.deposit_tx.output_index_for_address(self._redeem_script.hash160()) if self._model.deposit_tx else None  # nopep8

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
        return codecs.encode(self._wallet.sign(self.deposit_txid.encode('ascii'), self._customer_public_key).to_der(), 'hex_codec').decode() if self._model.deposit_tx else None  # nopep8

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
        """Get channel half-signed payment transaction.

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
