import os
import pytest
from unittest.mock import MagicMock
from two1.lib.bitcoin.crypto import HDPublicKey
from two1.lib.bitcoin.txn import Transaction
from two1.lib.blockchain.chain_provider import ChainProvider
from two1.lib.blockchain.insight_provider import InsightProvider
from two1.lib.blockchain.twentyone_provider import TwentyOneProvider
from two1.lib.blockchain.exceptions import DataProviderUnavailableError
from two1.lib.blockchain.exceptions import DataProviderError
from two1.lib.blockchain.block_cypher_provider import BlockCypherProvider


API_KEY_ID = os.environ.get("CHAIN_API_KEY_ID", None)
API_KEY_SECRET = os.environ.get("CHAIN_API_KEY_SECRET", None)
chain_key_present = pytest.mark.skipif(API_KEY_ID is None or API_KEY_SECRET is None,
                                       reason="CHAIN_API_KEY_ID or CHAIN_API_KEY_SECRET\
                                       is not available in env")

acct_pub_key = HDPublicKey.from_b58check("xpub68YdQASJ3w2RYS7XNT8HkLVjWqKeMD5uAxJR2vqXAh65j7izto1cVSwCNm7awAjjeYExqneCAZzt5xGETXZz1EXa9HntM5HzwdQ9551UErA")


chain_provider = ChainProvider(API_KEY_ID, API_KEY_SECRET)
twentyone_provider = TwentyOneProvider()
block_cypher_provider = BlockCypherProvider()
insight_provider = InsightProvider("http://insight.bitpay.com")
testnet_insight_provider = InsightProvider("http://testnet.blockexplorer.com")
#twentyone_provider = TwentyOneProvider("http://localhost:8000")


@pytest.mark.parametrize("provider, testnet",
                         [
                             (chain_provider, False),
                             (chain_provider, True),
                         ])
def test_get_balance(provider, testnet):
    cp = provider    
    cp.testnet = testnet

    if testnet:
        address_list = ["myTpteaBCwuHsDsoBQfrN4YjKEBpmoLBii"]
        exp_data = {'confirmed': 2000000, 'total': 2000000}
    else:
        address_list = ["17x23dNjXJLzGMev6R63uyRhMWP1VHawKc"]
        exp_data = {'confirmed': 5000000000, 'total': 5000000000}
    data = cp.get_balance(address_list)
    assert len(data) == 1
    assert list(data.keys())[0] == address_list[0]
    # test satoshi's address. If the following fails, Satoshi has moved coins
    assert data[address_list[0]] == exp_data

    # empty addresslist
    data = cp.get_balance([])
    assert len(data) == 0
    # bad address
    with pytest.raises(DataProviderError):
        data = cp.get_balance(["garbage"])
    # simulate server failure
    cp.server_url = "https://askdfjldsfjlk1j3ouhfsbjdafsjfhu.com"
    with pytest.raises(DataProviderUnavailableError):
        data = cp.get_balance(address_list)


chain_provider = ChainProvider(API_KEY_ID, API_KEY_SECRET)
twentyone_provider = TwentyOneProvider()


@pytest.mark.parametrize("provider, testnet",
                         [
                             (chain_provider, False),
                             (chain_provider, True),
                         ])
def test_utxo(provider, testnet):
    cp = provider
    cp.testnet = testnet

    if testnet:
        address_list = ["myTpteaBCwuHsDsoBQfrN4YjKEBpmoLBii"]
        data = cp.get_utxos(address_list)
        assert len(data) == 1
        assert set(address_list) == set(data.keys())
        assert len(data[address_list[0]]) == 2
    else:
        address_list = ["1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb"]
        data = cp.get_utxos(address_list)
        assert len(data) == 1
        assert list(data.keys())[0] == address_list[0]
        assert len(data[address_list[0]]) == 3
        # assert data[address_list[0]].transaction_hash ==
        address_list = ["1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb",
                        "1EX1E9n3bPA1zGKDV5iHY2MnM7n5tDfnfH"]
        data = cp.get_utxos(address_list)
        assert len(data) == 2
        assert set(address_list) == set(data.keys())
        assert len(data[address_list[0]]) == 3
        assert len(data[address_list[1]]) == 1


@pytest.mark.parametrize("provider, testnet",
                         [
                             (chain_provider, False),
                             (chain_provider, True),
                             (twentyone_provider, False),
                             (twentyone_provider, True),
                             (block_cypher_provider, False),
                             (block_cypher_provider, True),
                             (insight_provider, False),
                             (testnet_insight_provider, True)
                         ])
def test_get_transactions(provider, testnet):
    cp = provider
    cp.testnet = testnet
    if testnet:
        address_list = ["myTpteaBCwuHsDsoBQfrN4YjKEBpmoLBii"]
        data = cp.get_transactions(address_list)
        exp = (1, 2)
    else:
        address_list = ["1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb"]
        data = cp.get_transactions(address_list)
        exp = (1, 9)

    assert len(data) == exp[0]
    assert len(data[address_list[0]]) == exp[1]


@pytest.mark.parametrize("provider, testnet",
                         [
                             (chain_provider, False),
                             (chain_provider, True),
                             (twentyone_provider, False),
                             (twentyone_provider, True),
                             (block_cypher_provider, False),
                             (block_cypher_provider, True),
                             (insight_provider, False),
                             (testnet_insight_provider, True)
                         ])
def test_get_transactions_by_id(provider, testnet):
    cp = provider
    cp.testnet = testnet
    if testnet:
        txids = ["f19b101e3ede105b47c98dc54953f4dff195efb6654a168a22659585f92858b4"]
        exp_len = 1
    else:
        txids = ["6fd3c96d466cd465b40e59be14d023c27f1d0ca13075119d3d6baeebfc587b8c",
                 "d24f3b9f0aa7b6484bcea563f4c254bd24e8163906cbffc727c2b2dad43af61e"]
        exp_len = 2

    data = cp.get_transactions_by_id(txids)
    assert len(data) == exp_len
    for txid, txn in data.items():
        assert txid in txids
        assert isinstance(txn['transaction'], Transaction)


@pytest.mark.parametrize("provider, testnet",
                         [
                             (chain_provider, False),
                             (chain_provider, True),
                             (twentyone_provider, False),
                             (twentyone_provider, True),
                             (insight_provider, False),
                             (testnet_insight_provider, True)
                         ])
def test_provider_json_error(provider, testnet):
    cp = provider

    cp._session.request = MagicMock(return_value=
                                    type('obj', (object,), {'status_code': 400,
                                                            "json": lambda: "Not Json",
                                                            'text': "Error"})
                                    )
    if testnet:
        txids = ["f19b101e3ede105b47c98dc54953f4dff195efb6654a168a22659585f92858b4"]
        exp_len = 1
    else:
        txids = ["6fd3c96d466cd465b40e59be14d023c27f1d0ca13075119d3d6baeebfc587b8c",
                 "d24f3b9f0aa7b6484bcea563f4c254bd24e8163906cbffc727c2b2dad43af61e"]
        exp_len = 2
    cp.testnet = testnet
    with pytest.raises(DataProviderError):
        data = cp.get_transactions_by_id(txids)


@pytest.mark.parametrize("provider, testnet",
                         [
                             (chain_provider, False),
                             (chain_provider, True),
                             (twentyone_provider, False),
                             (twentyone_provider, True),
                             (block_cypher_provider, False),
                             (block_cypher_provider, True),
                             (insight_provider, False),
                             (testnet_insight_provider, True)
                         ])
def test_transaction_send(provider, testnet):
    cp = provider
    # test invalid transaction push
    if testnet:
        tx = "01000"
    else:
        tx = "01000"
    cp.testnet = testnet
    with pytest.raises(DataProviderError):
        data = cp.broadcast_transaction(tx)

