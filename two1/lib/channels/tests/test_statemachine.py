import codecs
import pytest

import two1.lib.bitcoin as bitcoin
import two1.lib.channels.statemachine as statemachine
import two1.lib.channels.walletwrapper as walletwrapper
import two1.lib.channels.tests.mock as mock


def test_redeem_script():
    # Redeem script parmaeters
    merchant_public_key = mock.MockPaymentChannelServer.PRIVATE_KEY.public_key
    customer_public_key = mock.MockTwo1Wallet.PRIVATE_KEY.public_key
    expiration_time = 1450223410
    serialized_redeem_script = "63210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac"

    # Test construction
    redeem_script = statemachine.PaymentChannelRedeemScript(merchant_public_key, customer_public_key, expiration_time)

    assert redeem_script.to_hex() == serialized_redeem_script
    assert redeem_script.merchant_public_key.compressed_bytes == merchant_public_key.compressed_bytes
    assert redeem_script.customer_public_key.compressed_bytes == customer_public_key.compressed_bytes
    assert redeem_script.expiration_time == expiration_time

    # Test deserialization
    redeem_script = statemachine.PaymentChannelRedeemScript.from_bytes(codecs.decode(serialized_redeem_script, "hex_codec"))

    assert redeem_script.to_hex() == serialized_redeem_script
    assert redeem_script.merchant_public_key.compressed_bytes == merchant_public_key.compressed_bytes
    assert redeem_script.customer_public_key.compressed_bytes == customer_public_key.compressed_bytes
    assert redeem_script.expiration_time == expiration_time

    # Test invalid deserialization
    with pytest.raises(ValueError):
        # Invalid length
        scr = bitcoin.Script(["OP_NOP"])
        statemachine.PaymentChannelRedeemScript.from_bytes(bytes(scr))
    with pytest.raises(ValueError):
        # Invalid opcode
        scr = bitcoin.Script.from_hex(serialized_redeem_script)
        scr[-1] = "OP_NOP"
        statemachine.PaymentChannelRedeemScript.from_bytes(bytes(scr))


def test_statemachine_create():
    """Test state machine transitions from initial state OPENING.

        Valid transitions:
            OPENING -> CONFIRMING_DEPOSIT   via create()
            OPENING -> READY                via create()

        Invalid transitions:
            OPENING -> OUTSTANDING          via pay()
            OPENING -> READY                via pay_ack() or pay_nack()
            OPENING -> CONFIRMING_SPEND     via close()
            OPENING -> CLOSED               via finalize()

    """
    # Create state machine
    model_data = {
        'url': 'test',
    }
    wallet = walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet())
    model = statemachine.PaymentChannelModel(**model_data)
    sm = statemachine.PaymentChannelStateMachine(model, wallet)

    # Assert state machine state
    assert sm.state == statemachine.PaymentChannelState.OPENING
    assert sm.balance_amount is None
    assert sm.deposit_amount is None
    assert sm.fee_amount is None
    assert sm.creation_time is None
    assert sm.expiration_time is None
    assert sm.deposit_tx_utxo_index is None
    assert sm.deposit_tx is None
    assert sm.deposit_txid is None
    assert sm.deposit_txid_signature is None
    assert sm.refund_tx is None
    assert sm.refund_txid is None
    assert sm.payment_tx is None
    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Check invalid transition OPENING -> READY via confirm()
    with pytest.raises(statemachine.StateTransitionError):
        sm.confirm()
    # Check invalid transition OPENING -> OUTSTANDING via pay()
    with pytest.raises(statemachine.StateTransitionError):
        sm.pay(1)
    # Check invalid transition OPENING -> READY via pay_ack()
    with pytest.raises(statemachine.StateTransitionError):
        sm.pay_ack()
    # Check invalid transition OPENING -> READY via pay_nack()
    with pytest.raises(statemachine.StateTransitionError):
        sm.pay_nack()
    # Check invalid transition OPENING -> CONFIRMING_SPEND via close()
    with pytest.raises(statemachine.StateTransitionError):
        sm.close(None)
    # Check invalid transition OPENING -> CLOSED via finalize()
    with pytest.raises(statemachine.StateTransitionError):
        sm.finalize("")

    # Channel parameters
    merchant_public_key = mock.MockPaymentChannelServer.PRIVATE_KEY.public_key.to_hex()
    deposit_amount = 100000
    expiration_time = 1450223410
    fee_amount = 10000

    # Check valid transition OPENING -> CONFIRMING_DEPOSIT via create()
    (deposit_tx, redeem_script) = sm.create(merchant_public_key, deposit_amount, expiration_time, fee_amount, zeroconf=False)
    assert deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert redeem_script == "63210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac"
    assert sm.state == statemachine.PaymentChannelState.CONFIRMING_DEPOSIT
    assert sm.balance_amount == 100000
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx is None
    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Reset state machine
    model = statemachine.PaymentChannelModel(**model_data)
    sm = statemachine.PaymentChannelStateMachine(model, wallet)

    # Check valid transition OPENING -> READY via create() with zeroconf=True
    (deposit_tx, redeem_script) = sm.create(merchant_public_key, deposit_amount, expiration_time, fee_amount, zeroconf=True)
    assert deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert redeem_script == "63210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac"
    assert sm.state == statemachine.PaymentChannelState.READY
    assert sm.balance_amount == 100000
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx is None
    assert sm.spend_tx is None
    assert sm.spend_txid is None


def test_statemachine_confirm():
    """Test state machine transitions from state CONFIRMING_DEPOSIT.

        Valid transitions:
            CONFIRMING_DEPOSIT -> READY             via confirm()
            CONFIRMING_DEPOSIT -> CONFIRMING_SPEND  via close()
            CONFIRMING_DEPOSIT -> CLOSED            via finalize()

        Invalid transitions:
            CONFIRMING_DEPOSIT -> READY             via pay_ack() or pay_nack()
            CONFIRMING_DEPOSIT -> OUTSTANDING       via pay()

    """
    # Create state machine
    model_data = {
        'url': 'test',
        'state': statemachine.PaymentChannelState.CONFIRMING_DEPOSIT,
        'creation_time': 42,
        'deposit_tx': bitcoin.Transaction.from_hex("010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"),
        'refund_tx': bitcoin.Transaction.from_hex("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"),
        'payment_tx': None,
        'spend_tx': None,
        'spend_txid': None,
        'min_output_amount': 1000,
    }
    wallet = walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet())
    model = statemachine.PaymentChannelModel(**model_data)
    sm = statemachine.PaymentChannelStateMachine(model, wallet)

    # Assert state machine state
    assert sm.state == statemachine.PaymentChannelState.CONFIRMING_DEPOSIT
    assert sm.balance_amount == 100000
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx is None
    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Check invalid transition CONFIRMING_DEPOSIT -> OUTSTANDING via pay()
    with pytest.raises(statemachine.StateTransitionError):
        sm.pay(1)
    # Check invalid transition CONFIRMING_DEPOSIT -> READY via pay_ack()
    with pytest.raises(statemachine.StateTransitionError):
        sm.pay_ack()
    # Check invalid transition CONFIRMING_DEPOSIT -> READY via pay_nack()
    with pytest.raises(statemachine.StateTransitionError):
        sm.pay_nack()

    # Check valid transition CONFIRMING_DEPOSIT -> READY via confirm()
    sm.confirm()
    assert sm.state == statemachine.PaymentChannelState.READY
    assert sm.balance_amount == 100000
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx is None
    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Reset state machine
    model = statemachine.PaymentChannelModel(**model_data)
    sm = statemachine.PaymentChannelStateMachine(model, wallet)

    # Check valid transition CONFIRMING_DEPOSIT -> CONFIRMING_SPEND via close()
    sm.close("2654e56291a542e99d26e1d2ba34d455031517453b6c7ae256c62e151ddc41cc")
    assert sm.state == statemachine.PaymentChannelState.CONFIRMING_SPEND
    assert sm.balance_amount == 100000
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx is None
    assert sm.spend_tx is None
    assert sm.spend_txid is "2654e56291a542e99d26e1d2ba34d455031517453b6c7ae256c62e151ddc41cc"

    # Reset state machine
    model = statemachine.PaymentChannelModel(**model_data)
    sm = statemachine.PaymentChannelStateMachine(model, wallet)

    # Check valid transition OPENING -> CLOSED via finalize()
    sm.finalize("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056")
    assert sm.state == statemachine.PaymentChannelState.CLOSED
    assert sm.balance_amount == 100000
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx is None
    assert sm.spend_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.spend_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"


def test_statemachine_pay():
    """Test state machine paying, transitions from
            READY -> OUTSTANDING -> READY.
    """
    # Create state machine
    model_data = {
        'url': 'test',
        'state': statemachine.PaymentChannelState.READY,
        'creation_time': 42,
        'deposit_tx': bitcoin.Transaction.from_hex("010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"),
        'refund_tx': bitcoin.Transaction.from_hex("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"),
        'payment_tx': None,
        'spend_tx': None,
        'spend_txid': None,
        'min_output_amount': 1000,
    }
    wallet = walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet())
    model = statemachine.PaymentChannelModel(**model_data)
    sm = statemachine.PaymentChannelStateMachine(model, wallet)

    # Assert state machine state
    assert sm.state == statemachine.PaymentChannelState.READY
    assert sm.balance_amount == 100000
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx is None
    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Test initial payment with amount 1, but nack it
    payment_tx = sm.pay(1)
    assert sm.state == statemachine.PaymentChannelState.OUTSTANDING
    sm.pay_nack()
    assert payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100e0758baae39dfb1c4402c37a3382ae96a34786734265ea2bc94977299dfd2573022047957838a067ad0bbd575ec219e71c1c750685f6a70da3baa9d294c8a8202d7b01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff02e8030000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488aca0860100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.state == statemachine.PaymentChannelState.READY
    assert sm.balance_amount == 100000
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx is None

    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Test initial payment with amount 1, and acknowledge it
    payment_tx = sm.pay(1)
    assert sm.state == statemachine.PaymentChannelState.OUTSTANDING
    sm.pay_ack()
    assert payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100e0758baae39dfb1c4402c37a3382ae96a34786734265ea2bc94977299dfd2573022047957838a067ad0bbd575ec219e71c1c750685f6a70da3baa9d294c8a8202d7b01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff02e8030000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488aca0860100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.state == statemachine.PaymentChannelState.READY
    assert sm.balance_amount == 99000
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100e0758baae39dfb1c4402c37a3382ae96a34786734265ea2bc94977299dfd2573022047957838a067ad0bbd575ec219e71c1c750685f6a70da3baa9d294c8a8202d7b01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff02e8030000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488aca0860100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Reset state machine
    model = statemachine.PaymentChannelModel(**model_data)
    sm = statemachine.PaymentChannelStateMachine(model, wallet)

    # Test initial payment with amount PAYMENT_TX_MIN_OUTPUT_AMOUNT + 1
    payment_tx = sm.pay(1001)
    assert sm.state == statemachine.PaymentChannelState.OUTSTANDING
    sm.pay_ack()
    assert payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009b47304402201638d4ca0760ce75d9aaf514f870076f2d68c43bcfcbed308ffe983b9d6f062e022036a5b377f2e32810bc235aaab2a885055fb6ff0348e25a8720b1c48ec228d3a301514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff02e9030000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac9f860100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.state == statemachine.PaymentChannelState.READY
    assert sm.balance_amount == 98999
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009b47304402201638d4ca0760ce75d9aaf514f870076f2d68c43bcfcbed308ffe983b9d6f062e022036a5b377f2e32810bc235aaab2a885055fb6ff0348e25a8720b1c48ec228d3a301514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff02e9030000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac9f860100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Test subsequent payment of 20000, but nack it
    payment_tx = sm.pay(20000)
    assert sm.state == statemachine.PaymentChannelState.OUTSTANDING
    sm.pay_nack()
    assert payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c4830450221009d19b49f540af728a3ce978bad1c4bf6d162a6f24f74dd11bde72e706521c08a02200ce0dd828018741434f74ee7a4c7bfb9e74c56d20246966b3a893d8bb13c871101514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff0209520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7f380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.state == statemachine.PaymentChannelState.READY
    assert sm.balance_amount == 98999
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009b47304402201638d4ca0760ce75d9aaf514f870076f2d68c43bcfcbed308ffe983b9d6f062e022036a5b377f2e32810bc235aaab2a885055fb6ff0348e25a8720b1c48ec228d3a301514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff02e9030000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac9f860100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Test subsequent payment of 20000
    payment_tx = sm.pay(20000)
    assert sm.state == statemachine.PaymentChannelState.OUTSTANDING
    sm.pay_ack()
    assert payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c4830450221009d19b49f540af728a3ce978bad1c4bf6d162a6f24f74dd11bde72e706521c08a02200ce0dd828018741434f74ee7a4c7bfb9e74c56d20246966b3a893d8bb13c871101514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff0209520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7f380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.state == statemachine.PaymentChannelState.READY
    assert sm.balance_amount == 78999
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c4830450221009d19b49f540af728a3ce978bad1c4bf6d162a6f24f74dd11bde72e706521c08a02200ce0dd828018741434f74ee7a4c7bfb9e74c56d20246966b3a893d8bb13c871101514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff0209520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7f380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Test excess payment of 80000
    with pytest.raises(statemachine.InsufficientBalanceError):
        payment_tx = sm.pay(80000)

    # Test excess payment of 79000
    with pytest.raises(statemachine.InsufficientBalanceError):
        payment_tx = sm.pay(79000)

    # Test subsequent payment of 1
    payment_tx = sm.pay(1)
    assert sm.state == statemachine.PaymentChannelState.OUTSTANDING
    sm.pay_ack()
    assert payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.state == statemachine.PaymentChannelState.READY
    assert sm.balance_amount == 78998
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Test remainder payment
    payment_tx = sm.pay(78998)
    assert sm.state == statemachine.PaymentChannelState.OUTSTANDING
    sm.pay_ack()
    assert payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009b4730440220064f50737f894e97d8f1c49b07f9206caacfeeb5f6fd0ff4a0fe1cce5668cdbf02207bbe2a71627d38c1c524c7b68b4c77ffb7b5edb78c0cb1dd8516ddf7d766acfc01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff02a0860100000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ace8030000000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.state == statemachine.PaymentChannelState.READY
    assert sm.balance_amount == 0
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009b4730440220064f50737f894e97d8f1c49b07f9206caacfeeb5f6fd0ff4a0fe1cce5668cdbf02207bbe2a71627d38c1c524c7b68b4c77ffb7b5edb78c0cb1dd8516ddf7d766acfc01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff02a0860100000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ace8030000000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_tx is None
    assert sm.spend_txid is None


def test_statemachine_close():
    """Test state machine close.

    Valid transitions:
        READY -> CONFIRMING_SPEND           via close()
        OUTSTANDING -> CONFIRMING_SPEND     via close()

    """
    # Create state machine
    model_data = {
        'url': 'test',
        'state': statemachine.PaymentChannelState.READY,
        'creation_time': 42,
        'deposit_tx': bitcoin.Transaction.from_hex("010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"),
        'refund_tx': bitcoin.Transaction.from_hex("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"),
        'payment_tx': bitcoin.Transaction.from_hex("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"),
        'spend_tx': None,
        'spend_txid': None,
        'min_output_amount': 1000,
    }
    wallet = walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet())
    model = statemachine.PaymentChannelModel(**model_data)
    sm = statemachine.PaymentChannelStateMachine(model, wallet)

    # Assert state machine state
    assert sm.state == statemachine.PaymentChannelState.READY
    assert sm.balance_amount == 78998
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Valid transition READY -> CONFIRMING_SPEND via close(None)
    sm.close(None)
    assert sm.state == statemachine.PaymentChannelState.CONFIRMING_SPEND
    assert sm.balance_amount == 78998
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Reset state machine
    model = statemachine.PaymentChannelModel(**model_data)
    sm = statemachine.PaymentChannelStateMachine(model, wallet)

    # Valid transition READY -> CONFIRMING_SPEND via close(<txid>)
    sm.close("afb48fb7c8f09a846b44df91f0704464785e61ef14da34e8a9b95cb0c1866968")
    assert sm.state == statemachine.PaymentChannelState.CONFIRMING_SPEND
    assert sm.balance_amount == 78998
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_tx is None
    assert sm.spend_txid is "afb48fb7c8f09a846b44df91f0704464785e61ef14da34e8a9b95cb0c1866968"

    # Reset state machine
    model = statemachine.PaymentChannelModel(**model_data)
    sm = statemachine.PaymentChannelStateMachine(model, wallet)

    # Valid transition OUTSTANDING -> CONFIRMING_SPEND via close(<txid>)
    sm.pay(1)
    assert sm.state == statemachine.PaymentChannelState.OUTSTANDING
    sm.close("afb48fb7c8f09a846b44df91f0704464785e61ef14da34e8a9b95cb0c1866968")
    assert sm.state == statemachine.PaymentChannelState.CONFIRMING_SPEND
    assert sm.balance_amount == 78998
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_tx is None
    assert sm.spend_txid is "afb48fb7c8f09a846b44df91f0704464785e61ef14da34e8a9b95cb0c1866968"


def test_statemachine_finalize():
    """Test state machine finalize.

    Valid transitions:
        CONFIRMING_SPEND -> CLOSED  via finalize()
        READY -> CLOSED             via finalize()

    """
    # Create state machine
    model_data = {
        'url': 'test',
        'state': statemachine.PaymentChannelState.CONFIRMING_SPEND,
        'creation_time': 42,
        'deposit_tx': bitcoin.Transaction.from_hex("010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"),
        'refund_tx': bitcoin.Transaction.from_hex("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"),
        'payment_tx': bitcoin.Transaction.from_hex("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"),
        'spend_tx': None,
        'spend_txid': None,
        'min_output_amount': 1000,
    }
    wallet = walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet())
    model = statemachine.PaymentChannelModel(**model_data)
    sm = statemachine.PaymentChannelStateMachine(model, wallet)

    # Assert state machine state
    assert sm.state == statemachine.PaymentChannelState.CONFIRMING_SPEND
    assert sm.balance_amount == 78998
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_tx is None
    assert sm.spend_txid is None

    # Valid finalize with refund tx
    sm.finalize("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056")
    assert sm.state == statemachine.PaymentChannelState.CLOSED
    assert sm.balance_amount == 100000
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.spend_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"

    # Reset state machine
    model = statemachine.PaymentChannelModel(**model_data)
    sm = statemachine.PaymentChannelStateMachine(model, wallet)

    # Valid finalize with payment tx
    sm.finalize("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e00000000e5483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01483045022100ee02cd312b33e78d7dd6d9044f47577a224038fa731ad34ca0ea4870575d6223022073124ecd6c63042ec6a99b34ba6d926524c6491fb1440eaa21177329f542e97501514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000")
    assert sm.state == statemachine.PaymentChannelState.CLOSED
    assert sm.balance_amount == 78998
    assert sm.deposit_amount == 100000
    assert sm.fee_amount == 10000
    assert sm.creation_time != 0
    assert sm.expiration_time == 1450223410
    assert sm.deposit_tx_utxo_index == 0
    assert sm.deposit_tx == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"
    assert sm.deposit_txid == "7e1a558c84abd5aaf57999557f4a7205d4b69241b7c9cab6c0795fdd663a51ef"
    assert sm.deposit_txid_signature == "30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27"
    assert sm.refund_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.refund_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"
    assert sm.payment_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e00000000e5483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01483045022100ee02cd312b33e78d7dd6d9044f47577a224038fa731ad34ca0ea4870575d6223022073124ecd6c63042ec6a99b34ba6d926524c6491fb1440eaa21177329f542e97501514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_txid == "247412297242f1849a9fd8ef7b1acabdb07465da32ab5240d8ba425876a43104"

    # Reset state machine
    model = statemachine.PaymentChannelModel(**model_data)
    sm = statemachine.PaymentChannelStateMachine(model, wallet)

    # Invalid finalize with wrong refund tx
    with pytest.raises(statemachine.InvalidTransactionError):
        sm.finalize("010000000191efdfed621ebd3b3ad4044097086c5df75589f424261bfec6371e186a86725d010000009c47304402204ececbed85c20f3bae5393d68d1717cb258a9532e9976bf1e75103b1876427010220273c1440fff7b330d41407f83f871fcaf178ea0a413045424a48825821736aae0101004c50632102f1fff97def324ddea032fed4c8249113b8dce12aaf614d11bb833e587072c8a9ad6704a9a07056b1756821026179020dba5ad8275cf6389a85a00c08f3597bb8617af8148f249a4cd719ab39ac0000000001888a0100000000001976a914314d768ce14fc1f5dffdac1e4a0ed13705d4a4a688aca9a07056")

    # Invalid finalize with wrong payment tx
    with pytest.raises(statemachine.InvalidTransactionError):
        sm.finalize("010000000191efdfed621ebd3b3ad4044097086c5df75589f424261bfec6371e186a86725d01000000e4473044022049d1f41a867aa84266a1f5d2f6283d2b1e6ee07d068a098615d7a7868a96ed78022060c798cbb4740277cb095c399fb10ebd2716894c203527b0e6e3ed797400d10701483045022100de7c4c35c263cc2e1df1f2b06925225a72b9cb28e3b8bae4db7b078a1e4ac25c022031103dbe8993e94daa119d4c78e0bf52d3513e152d8b5bc192f8cb26ac3c683901514c50632102f1fff97def324ddea032fed4c8249113b8dce12aaf614d11bb833e587072c8a9ad6704a9a07056b1756821026179020dba5ad8275cf6389a85a00c08f3597bb8617af8148f249a4cd719ab39acffffffff02a0860100000000001976a914ffffb9d45c6cb46133f55a83c2fde9edb1c5f50688ace8030000000000001976a914314d768ce14fc1f5dffdac1e4a0ed13705d4a4a688ac00000000")

    # Invalid finalize with half-signed payment tx
    with pytest.raises(statemachine.InvalidTransactionError):
        sm.finalize("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000")

    # Invalid finalize with invalid tx
    with pytest.raises(statemachine.InvalidTransactionError):
        sm.finalize("010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000")

    # Valid transition CLOSED -> CLOSED via finalize()
    # Finalize with valid payment
    sm.finalize("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e00000000e5483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01483045022100ee02cd312b33e78d7dd6d9044f47577a224038fa731ad34ca0ea4870575d6223022073124ecd6c63042ec6a99b34ba6d926524c6491fb1440eaa21177329f542e97501514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000")
    assert sm.state == statemachine.PaymentChannelState.CLOSED
    assert sm.balance_amount == 78998
    assert sm.spend_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e00000000e5483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01483045022100ee02cd312b33e78d7dd6d9044f47577a224038fa731ad34ca0ea4870575d6223022073124ecd6c63042ec6a99b34ba6d926524c6491fb1440eaa21177329f542e97501514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"
    assert sm.spend_txid == "247412297242f1849a9fd8ef7b1acabdb07465da32ab5240d8ba425876a43104"
    # Finalize with refund
    sm.finalize("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056")
    assert sm.state == statemachine.PaymentChannelState.CLOSED
    assert sm.balance_amount == 100000
    assert sm.spend_tx == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"
    assert sm.spend_txid == "e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba"

    # Invalid transition CLOSED -> OUTSTANDING via pay()
    with pytest.raises(statemachine.StateTransitionError):
        sm.pay(1)
    # Invalid transition CLOSED -> READY via pay_ack()
    with pytest.raises(statemachine.StateTransitionError):
        sm.pay_ack()
    # Invalid transition CLOSED -> READY via pay_nack()
    with pytest.raises(statemachine.StateTransitionError):
        sm.pay_nack()
    # Invalid transition CLOSED -> CONFIRMING_DEPOSIT via close()
    with pytest.raises(statemachine.StateTransitionError):
        sm.close(None)
