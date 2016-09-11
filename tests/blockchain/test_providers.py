import pytest
from two1.bitcoin.crypto import HDPublicKey
from two1.bitcoin.txn import Transaction
from two1.blockchain.twentyone_provider import TwentyOneProvider
from two1.blockchain.exceptions import DataProviderError


acct_pub_key = HDPublicKey.from_b58check(
    "xpub68YdQASJ3w2RYS7XNT8HkLVjWqKeMD5uAxJR2vqXAh65j7izto1cVSwCNm7awAjjeYExqneCAZzt5xGETXZz1EXa9HntM5HzwdQ9551UErA")

twentyone_provider = TwentyOneProvider()
stage_twentyone_provider = TwentyOneProvider("http://blockchain.21-stage.co")


@pytest.mark.parametrize("provider, testnet",
                         [
                             (twentyone_provider, False),
                             (twentyone_provider, True),
                             (stage_twentyone_provider, False),
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
                             (twentyone_provider, False),
                             (stage_twentyone_provider, False),
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
                             (twentyone_provider, False),
                             (twentyone_provider, True),
                             (stage_twentyone_provider, False),
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
        cp.broadcast_transaction(tx)
