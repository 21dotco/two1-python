import os
import pytest
from two1.lib.bitcoin.crypto import HDPublicKey
from two1.lib.bitcoin.txn import Transaction
from two1.lib.blockchain.chain_provider import ChainProvider
from two1.lib.blockchain.twentyone_provider import TwentyOneProvider
from two1.lib.blockchain.exceptions import DataProviderUnavailableError
from two1.lib.blockchain.exceptions import DataProviderError


API_KEY_ID = os.environ.get("CHAIN_API_KEY_ID", None)
API_KEY_SECRET = os.environ.get("CHAIN_API_KEY_SECRET", None)
chain_key_present = pytest.mark.skipif(API_KEY_ID is None or API_KEY_SECRET is None,
                                       reason="CHAIN_API_KEY_ID or CHAIN_API_KEY_SECRET\
                                       is not available in env")

acct_pub_key = HDPublicKey.from_b58check("xpub68YdQASJ3w2RYS7XNT8HkLVjWqKeMD5uAxJR2vqXAh65j7izto1cVSwCNm7awAjjeYExqneCAZzt5xGETXZz1EXa9HntM5HzwdQ9551UErA")


chain_provider = ChainProvider(API_KEY_ID, API_KEY_SECRET)
twentyone_provider = TwentyOneProvider("https://dotco-devel-pool2.herokuapp.com")


@pytest.mark.parametrize("provider",
                         [
                             (chain_provider),
                             (twentyone_provider)
                         ])
def test_get_balance(provider):
    cp = provider
    address_list = ["17x23dNjXJLzGMev6R63uyRhMWP1VHawKc"]
    data = cp.get_balance(address_list)
    assert len(data) == 1
    assert list(data.keys())[0] == address_list[0]
    # test satoshi's address. If the following fails, Satoshi has moved coins
    assert data[address_list[0]] == {'confirmed': 5000000000,
                                     'total': 5000000000}

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
twentyone_provider = TwentyOneProvider("https://dotco-devel-pool2.herokuapp.com")


@pytest.mark.parametrize("provider",
                         [
                             (chain_provider),
                             (twentyone_provider)
                         ])
def test_utxo(provider):
    cp = provider
    address_list = ["1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb"]
    data = cp.get_utxos(address_list)
    assert len(data) == 1
    assert list(data.keys())[0] == address_list[0]
    assert len(data[address_list[0]]) == 3
#    assert data[address_list[0]].transaction_hash ==
    address_list = ["1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb", "1EX1E9n3bPA1zGKDV5iHY2MnM7n5tDfnfH"]
    data = cp.get_utxos(address_list)
    assert len(data) == 2
    assert set(address_list) == set(data.keys())
    assert len(data[address_list[0]]) == 3
    assert len(data[address_list[1]]) == 1


@pytest.mark.parametrize("provider",
                         [
                             (chain_provider),
                             (twentyone_provider)
                         ])
def test_get_transactions(provider):
    cp = provider
    address_list = ["1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb"]
    data = cp.get_transactions(address_list)
    assert len(data) == 1
    assert len(data[address_list[0]]) == 9


@pytest.mark.parametrize("provider",
                         [
                             (chain_provider),
                             (twentyone_provider)
                         ])
def test_get_transactions_by_id(provider):
    cp = provider
    txids = ["6fd3c96d466cd465b40e59be14d023c27f1d0ca13075119d3d6baeebfc587b8c",
             "d24f3b9f0aa7b6484bcea563f4c254bd24e8163906cbffc727c2b2dad43af61e"]
    data = cp.get_transactions_by_id(txids)
    assert len(data) == 2
    for txid, txn in data.items():
        assert txid in txids
        assert isinstance(txn, Transaction)
