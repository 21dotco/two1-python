import codecs
import pytest

import two1.lib.bitcoin as bitcoin
import two1.lib.channels.statemachine as statemachine
import two1.lib.channels.walletwrapper as walletwrapper
import two1.lib.channels.tests.mock as mock


@pytest.fixture(params=[
    walletwrapper.Two1WalletWrapper(mock.MockTwo1Wallet())
])
def wallet(request):
    return request.param


def test_walletwrapper(wallet):
    # Check get_public_key()
    assert wallet.get_public_key().compressed_bytes == bitcoin.PublicKey.from_hex("04ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dc3ad232846aad9dc0ecc9328a79956522f532ef9e67435bdc05900cf9f4d1383").compressed_bytes

    # Payment Channel with 100000 deposit, 1000 minimum output, 10000 fee
    redeem_script = statemachine.PaymentChannelRedeemScript(mock.MockPaymentChannelServer.PRIVATE_KEY.public_key, mock.MockTwo1Wallet.PRIVATE_KEY.public_key, 1450223410)

    # Check create_deposit_tx()
    deposit_tx = wallet.create_deposit_tx(redeem_script.address(), 100000 + 1000, 10000)
    assert deposit_tx.to_hex() == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006b483045022100c45e5bd8d00caa1cd3ad46e078ec132c9c505b3168d1d1ffe6285cf054f54ed302203ea12c4203ccee8a9de616cc22f081eed47a78660ce0a01cb3a97e302178a573012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff0198b101000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"

    # Check create_refund_tx()
    refund_tx = wallet.create_refund_tx(deposit_tx, redeem_script, redeem_script.expiration_time, 10000)
    assert refund_tx.to_hex() == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009d483045022100d00fb043ab32361c4e574e4f7f59ba0b3d1c2fbe758c3d26555cb3748e3270050220729cb95327245aa6f428f87b1e13cbc9c82dfa6dbc2bac0fc4641fc720dc0b220101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacfeffffff01888a0100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"

    # Check create_payment_tx() with 1000
    payment_tx = wallet.create_payment_tx(deposit_tx, redeem_script, 1000, 10000)
    assert payment_tx.to_hex() == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100e0758baae39dfb1c4402c37a3382ae96a34786734265ea2bc94977299dfd2573022047957838a067ad0bbd575ec219e71c1c750685f6a70da3baa9d294c8a8202d7b01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff02e8030000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488aca0860100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"

    # Check create_payment_tx() with 21001
    payment_tx = wallet.create_payment_tx(deposit_tx, redeem_script, 21001, 10000)
    assert payment_tx.to_hex() == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c4830450221009d19b49f540af728a3ce978bad1c4bf6d162a6f24f74dd11bde72e706521c08a02200ce0dd828018741434f74ee7a4c7bfb9e74c56d20246966b3a893d8bb13c871101514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff0209520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7f380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"

    # Check create_payment_tx() with 21002
    payment_tx = wallet.create_payment_tx(deposit_tx, redeem_script, 21002, 10000)
    assert payment_tx.to_hex() == "0100000001ef513a66dd5f79c0b6cac9b74192b6d405724a7f559979f5aad5ab848c551a7e000000009c483045022100bd2a89446c9d5985ee711747f35b8e367a90eb13970aec1b3a3ad11e01da7ac602205405fe99d5fe590fb13f0b7698e306e3bbcdd83855e156eb8e9a8901f887229f01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff020a520000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac7e380100000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"

    # Check sign()
    sig = wallet.sign(str(deposit_tx.hash).encode('ascii'), redeem_script.customer_public_key)
    assert sig.to_der() == codecs.decode("30450221008f51b6565a8ee67c32529ed840116c44e1f60a628c51ac59720cc8c6df1b5eab02204ccc32c89f81425f483c64c6f8dd77e57eefd3b6a5b7548d1875f5ef3f86cf27", 'hex_codec')


    # Payment Channel with 300000 deposit, 1000 minimum output, 20000 fee
    redeem_script = statemachine.PaymentChannelRedeemScript(mock.MockPaymentChannelServer.PRIVATE_KEY.public_key, mock.MockTwo1Wallet.PRIVATE_KEY.public_key, 1450223410)

    # Check create_deposit_tx()
    deposit_tx = wallet.create_deposit_tx(redeem_script.address(), 300000 + 1000, 20000)
    assert deposit_tx.to_hex() == "010000000119de54dd7043927219cca4c06cc8b94c7c862b6486b0f989ea4c6569fb34383d010000006a4730440220047aed529aa7c5d1c576a80e3d831e3fee6b1bca9375df742867578e098fea32022029b7fdeda98ef67458bfd91a18df43e8e1ca13f700b87bd366f5dc49588da0c8012103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dffffffff01e8e504000000000017a9149bc3354ccfd998cf16628449b940e6914210f1098700000000"

    # Check create_refund_tx()
    refund_tx = wallet.create_refund_tx(deposit_tx, redeem_script, redeem_script.expiration_time, 20000)
    assert refund_tx.to_hex() == "0100000001dd7962b5c22a192ed7f7e6327816038a765dfd6d40c871c681461d34b86caff2000000009d483045022100a54c4494f2a6b5877364b52d010ec68512369d73eb05b662875c47ae53ab3e8f02203fbd1fe956afaecd8c7de6ffd1670a86b5ddead1aa16641bf3e3075e6e79f6130101004c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacfeffffff01c8970400000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac32a77056"

    # Check create_payment_tx() with 1000
    payment_tx = wallet.create_payment_tx(deposit_tx, redeem_script, 1000, 20000)
    assert payment_tx.to_hex() == "0100000001dd7962b5c22a192ed7f7e6327816038a765dfd6d40c871c681461d34b86caff2000000009c483045022100be91f07d2d1542e3d3634aea874c46a7cc5d9a8d91889823656c114e187432f90220626998d4026665b0337b0acf536e591e1f84c04ebcfc959a4500bd9491e6597501514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff02e8030000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ace0930400000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"

    # Check create_payment_tx() with 5000
    payment_tx = wallet.create_payment_tx(deposit_tx, redeem_script, 5000, 20000)
    assert payment_tx.to_hex() == "0100000001dd7962b5c22a192ed7f7e6327816038a765dfd6d40c871c681461d34b86caff2000000009b4730440220724d1417af1af427129ec1508d4c34b05171bdbf5561a79a8e3e310962975de802200a069a951e65a1c450d8208f3ebd1a97bbf9bd8fafd2da79796253bc543fc61301514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff0288130000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488ac40840400000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"

    # Check create_payment_tx() with 7123
    payment_tx = wallet.create_payment_tx(deposit_tx, redeem_script, 7123, 20000)
    assert payment_tx.to_hex() == "0100000001dd7962b5c22a192ed7f7e6327816038a765dfd6d40c871c681461d34b86caff2000000009b4730440220315bb43d150e2eb1311235c8e0e93b3b9173e5f4d3dc48b190e6a5cebf9221e80220767d24f5bf24ad39338843918e1004176b2d81db8eb214d2cc2da4bccfb347df01514c5063210316f5d704b828c3252432886a843649730e08ae01bbbd5c6bde63756d7f54f961ad670432a77056b175682103ee071c95cb772e57a6d8f4f987e9c61b857e63d9f3b5be7a84bdba0b5847099dacffffffff02d31b0000000000001976a914a5f30391271dfccc133d321960ffe1dccc88e1b488acf57b0400000000001976a914b42fb00f78266bba89feee86036df44401320fba88ac00000000"

    # Check sign()
    sig = wallet.sign(str(deposit_tx.hash).encode('ascii'), redeem_script.customer_public_key)
    assert sig.to_der() == codecs.decode("30440220075489106453c13a48eeb71d69b7dae439b2c68afa16785a6b4228f568bf805202203f948072a04582d12fa33f0e962af35c536453043244a5681a2643bb2738438c", 'hex_codec')
