import pytest
from two1.wallet.chain_txn_data_provider import ChainTransactionDataProvider
from two1.wallet.txn_data_provider import DataProviderUnAvailable


API_KEY = 'a96f8c3c18abe407757713a09614ba0b'
API_SECRET = 'a13421f9347421e88c17d8388638e311'


def test_get_balance():
    ctd = ChainTransactionDataProvider(API_KEY, API_SECRET)
    address_list = ["17x23dNjXJLzGMev6R63uyRhMWP1VHawKc"]
    data = ctd.get_balance(address_list)
    assert len(data) == 1
    assert list(data.keys())[0] == address_list[0]
    # test satoshi's address. If the following fails, Satoshi has moved coins
    assert data[address_list[0]] == (5000000000, 0)

    # empty addresslist
    data = ctd.get_balance([])
    assert len(data) == 0
    # bad address
    with pytest.raises(ValueError):
        data = ctd.get_balance(["garbage"])
    # simulate server failure
    ctd.server_url = "https://askdfjldsfjlk1j3ouhfsbjdafsjfhu.com"
    with pytest.raises(DataProviderUnAvailable):
        data = ctd.get_balance(address_list)


def test_utxo():
    ctd = ChainTransactionDataProvider(API_KEY, API_SECRET)
    address_list = ["1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb"]
    data = ctd.get_utxo(address_list)
    assert len(data) == 1
    assert list(data.keys())[0] == address_list[0]
    assert len(data[address_list[0]]) == 3
#    assert data[address_list[0]].transaction_hash ==
    address_list = ["1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb", "1EX1E9n3bPA1zGKDV5iHY2MnM7n5tDfnfH"]
    data = ctd.get_utxo(address_list)
    assert len(data) == 2
    assert set(address_list) == set(data.keys())
    assert len(data[address_list[0]]) == 3
    assert len(data[address_list[1]]) == 1


def test_get_transactions():
    ctd = ChainTransactionDataProvider(API_KEY, API_SECRET)
    address_list = ["1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb"]
    data = ctd.get_transactions(address_list)
    assert len(data) == 1
    assert len(data[address_list[0]]) == 9
