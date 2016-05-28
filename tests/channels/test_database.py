import pytest

import two1.bitcoin as bitcoin
import two1.channels.statemachine as statemachine
import two1.channels.database as database


@pytest.fixture(params=[
    database.Sqlite3Database(":memory:"),
])
def db(request):
    return request.param


def test_database_sqlite3_create(db):
    # Model test vectors
    models = [
        statemachine.PaymentChannelModel(
            url='test0',
            state=statemachine.PaymentChannelState.OPENING,
        ),
        statemachine.PaymentChannelModel(
            url='test1',
            state=statemachine.PaymentChannelState.READY,
            creation_time=42,
            deposit_tx=bitcoin.Transaction.from_hex("010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"),  # nopep8
            refund_tx=bitcoin.Transaction.from_hex("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"),  # nopep8
            payment_tx=bitcoin.Transaction.from_hex("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"),  # nopep8
            spend_tx=None,
            spend_txid=None,
            min_output_amount=1000,
        ),
        statemachine.PaymentChannelModel(
            url='test2',
            state=statemachine.PaymentChannelState.CLOSED,
            creation_time=42,
            deposit_tx=bitcoin.Transaction.from_hex("010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"),  # nopep8
            refund_tx=bitcoin.Transaction.from_hex("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"),  # nopep8
            payment_tx=bitcoin.Transaction.from_hex("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"),  # nopep8
            spend_tx=bitcoin.Transaction.from_hex("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c47304402207c866a5d8d46c767975c95b9fa65051578898445c85f367c4d6b56c6b795491102202db45315bfd27aa19bd7156aa70aed48ebe331c88297711ff675da5ff069f7b90101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dac0000000001888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"),  # nopep8
            spend_txid="e49cef2fbaf7b6590eb502e4b143f24d5d95ca2e255b166f3b40bef786a32bba",
            min_output_amount=1000,
        ),
    ]

    for i in range(len(models)):
        # Add the model
        with db:
            db.create(models[i])

        # List all models
        with db:
            urls = db.list()
        assert len(urls) == (i + 1)
        assert all([urls[j] == models[j].url for j in range(i + 1)])

        # Expect exception when trying to add model again
        with pytest.raises(Exception):
            with db:
                db.create(models[i])

        # Read-back model
        with db:
            model = db.read(models[i].url)

        # Check model consistency
        assert model.url == models[i].url
        assert model.state == models[i].state
        assert model.creation_time == models[i].creation_time \
            if models[i].creation_time is not None else model.creation_time is None
        assert bytes(model.deposit_tx) == bytes(models[i].deposit_tx) \
            if models[i].deposit_tx is not None else model.deposit_tx is None
        assert bytes(model.refund_tx) == bytes(models[i].refund_tx) \
            if models[i].refund_tx is not None else model.refund_tx is None
        assert bytes(model.payment_tx) == bytes(models[i].payment_tx) \
            if models[i].payment_tx is not None else model.payment_tx is None
        assert bytes(model.spend_tx) == bytes(models[i].spend_tx) \
            if models[i].spend_tx is not None else model.spend_tx is None
        assert model.spend_txid == models[i].spend_txid
        assert model.min_output_amount == models[i].min_output_amount

    # Update models
    models[0].creation_time = 1124345
    models[1].payment_tx = bitcoin.Transaction.from_hex("0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009b4730440220064f50737f894e97d8f1c49b07f9206caacfeeb5f6fd0ff4a0fe1cce5668cdbf02207bbe2a71627d38c1c524c7b68b4c77ffb7b5edb78c0cb1dd8516ddf7d766acfc01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff02a0860100000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ace8030000000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000")  # nopep8
    for i in range(len(models)):
        with db:
            db.update(models[i])

    # Read-back and compare all models
    for i in range(len(models)):
        # Read-back model
        with db:
            model = db.read(models[i].url)

        # CHeck model consistency
        assert model.url == models[i].url
        assert model.state == models[i].state
        assert model.creation_time == models[i].creation_time \
            if models[i].creation_time is not None else model.creation_time is None
        assert bytes(model.deposit_tx) == bytes(models[i].deposit_tx) \
            if models[i].deposit_tx is not None else model.deposit_tx is None
        assert bytes(model.refund_tx) == bytes(models[i].refund_tx) \
            if models[i].refund_tx is not None else model.refund_tx is None
        assert bytes(model.payment_tx) == bytes(models[i].payment_tx) \
            if models[i].payment_tx is not None else model.payment_tx is None
        assert bytes(model.spend_tx) == bytes(models[i].spend_tx) \
            if models[i].spend_tx is not None else model.spend_tx is None
        assert model.spend_txid == models[i].spend_txid
        assert model.min_output_amount == models[i].min_output_amount
