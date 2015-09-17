import pytest
from two1.bitcoin.crypto import HDPublicKey
from two1.bitcoin.txn import Transaction
from two1.blockchain.chain_provider import ChainProvider
from two1.blockchain.exceptions import DataProviderUnavailableError
from two1.blockchain.exceptions import DataProviderError


API_KEY = 'a96f8c3c18abe407757713a09614ba0b'
API_SECRET = 'a13421f9347421e88c17d8388638e311'

acct_pub_key = HDPublicKey.from_b58check("xpub68YdQASJ3w2RYS7XNT8HkLVjWqKeMD5uAxJR2vqXAh65j7izto1cVSwCNm7awAjjeYExqneCAZzt5xGETXZz1EXa9HntM5HzwdQ9551UErA")

def test_get_balance():
    cp = ChainProvider(API_KEY, API_SECRET)
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

def test_utxo():
    cp = ChainProvider(API_KEY, API_SECRET)
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

def test_get_transactions():
    cp = ChainProvider(API_KEY, API_SECRET)
    address_list = ["1K4nPxBMy6sv7jssTvDLJWk1ADHBZEoUVb"]
    data = cp.get_transactions(address_list)
    assert len(data) == 1
    assert len(data[address_list[0]]) == 9

def test_get_transactions_by_id():
    cp = ChainProvider(API_KEY, API_SECRET)
    txids = ["6fd3c96d466cd465b40e59be14d023c27f1d0ca13075119d3d6baeebfc587b8c",
             "d24f3b9f0aa7b6484bcea563f4c254bd24e8163906cbffc727c2b2dad43af61e"]
    data = cp.get_transactions_by_id(txids)
    assert len(data) == 2
    for txid, txn in data.items():
        assert txid in txids
        assert isinstance(txn, Transaction)
    
def test_hd():
    cp = ChainProvider(API_KEY, API_SECRET)

    used_address = '1K3m1EwuxMCUTsS3wN2k7sXYHzABCVJSug'
    
    # Only has 1 key used, but give it 10, just to make sure
    balances = cp.get_balance_hd(acct_pub_key, 10, 10)

    assert balances[used_address] == {'confirmed': 716871, 'total': 716871}

    for addr, balance in balances.items():
        if addr != used_address:
            assert balance == {'confirmed': 0, 'total': 0}

    # Get txns
    txns = cp.get_transactions_hd(acct_pub_key, 10, 10)

    assert len(txns[used_address]) == 21
    for addr, addr_txns in txns.items():
        if addr != used_address:
            assert not addr_txns

    used_txns = ["c27533361f8ac7cfae56c4a61c9f87b24957b52b7cbe093f35d4bb0729eb7c3f",
                 "fae5f5f50ac0791557e9ecda0d0005ab58ecaba19425f62c01765b27ea330c1c",
                 "ff39ec74f7a46bfc81b73451878452a0cb691fd9c33e164a78aeab0d0d24dcda",
                 "064bd300e05468ce8a2ab65a60e0812218b5960137a551469c32e0b93f1e3b14",
                 "f1bc1f133bc9004c58936b0fa4a2dd08aa58cad08513ae128f6dadfa2d89ec46",
                 "faa2e502b6c3e6058d39d56034af4c3cfcc2385bed84a07ac00ef359139fe11e",
                 "54a13e6a34dcc2539a7c36e863b36e9c6cc53495afa75207de6d78c0363ec72c",
                 "dcf329a70e98e9f84002e08e0666f9465b9c1b85daaa96f61aac7da57769d398",
                 "1d3b908fb93d34d084da9edcf4dc408e46fabad27b44188995c20fcef1900f2a",
                 "7cce84c461f49405a8d94fcb714eaeca5eb5e23f7503ce17a20aff5a3f7398ab",
                 "13fcf2d5b71083fe4a01fe13a0edfc6ed095127691040b40ccbe1c479589b436",
                 "0eb4fb40a70a1f0164b5950d1d3c09f1ab5a9a8b55680127e94d7649ef505e97",
                 "637ca6cea839ce73a3f917afb2d9387c565caa3509691238f8704db18f985b40",
                 "7b8a93802bf5e83d86207dacd828636b17788998e49ac1c671f866c6594fd0b9",
                 "4944b93e6639acc99b3fac6e634e0be13d90eea84a90e67e36acc0b4519be86b",
                 "84b486511880c508353a395d8b6c3c30df932c8a1c7bdc7dd31da749017bf713",
                 "edd2ea9914d1ec4a4cd006328123d8ce6ccf051511640540d20d83d4c8715e5a",
                 "f338532c62f731fcba78a471ff4ce5dc569634a07c783daee97cd9ba6e741de2",
                 "b8693c87cf5847fcc90dfdb721d96ddafdf7647491af3a0742af0f5eae048332",
                 "d3d11ef7ebeb9d600ee7d8d6571e78a8c35dec1918f5c855260c05a05f9f346c",
                 "f2d0f0862da48d0b706f2f7057f129ab14e6d6da553d412d30da8049460f650d"]

    for txn in txns[used_address]:
        assert str(txn.hash) in used_txns

    # Now test get_utxos_hd - all of the above txns are unspent.
    utxos = cp.get_utxos_hd(acct_pub_key, 10, 10)
    
    assert len(utxos[used_address]) == 23 # There are 2 txns that have 2 outpoints coming to this address.
    for utxo in utxos[used_address]:
        assert str(utxo.transaction_hash) in used_txns
