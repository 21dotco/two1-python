import inspect
import os.path
import time

from two1.blockchain.twentyone_provider import TwentyOneProvider
from two1.bitcoin.hash import Hash
from two1.wallet.cache_manager import CacheManager
from two1.wallet.wallet_txn import WalletTransaction


this_file_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

cm = CacheManager()
dp = TwentyOneProvider()


def test_addresses():
    cm.insert_address(0, 0, 0, "15qCydrcqURADXJHrtMW9m6SpPTa3kqkQb")
    cm.insert_address(0, 0, 1, "15hyvVXH2eJnakwhpqKBf5oTCa3o2bp8m8")
    cm.insert_address(0, 0, 19, "17TNXJSWjBdMpHAkSfuyfVKSvb3rLuWZqQ")
    cm.insert_address(0, 1, 0, "1BbPtYsbBPFRCwnU5RuMTttraghXQ5JSZm")
    cm.insert_address(0, 1, 1, "1JuFprygqrra7vwYzrpBkGUbXjYao3RaR3")
    cm.insert_address(0, 1, 2, "16iY4btKxq9tz7sSZnva3691RYigcWDaSv")
    cm.insert_address(0, 1, 3, "1MDXXbB8JBV4bZU4buzxV456RAFqL7Z93f")
    cm.insert_address(0, 1, 4, "18vZXvhQAg8Fd8Ym7fbDUiBQS8o1iYDnkT")
    cm.insert_address(0, 1, 5, "1A9Gn3srogH6nNSqyWRf4YSBvvarvJzepc")
    cm.insert_address(0, 1, 6, "1FHkYaLSQ9A32PAopjLiBdZr1XQ5TueJWr")
    cm.insert_address(0, 1, 7, "1FAqCWr2EkAz43JzPRsdqLKBQeLJo4Tc7M")
    cm.insert_address(0, 1, 8, "12gR11fhqeDWpERmTfggVKUpDLfkq1dKbZ")
    cm.insert_address(0, 1, 9, "1Pr6wKbrfbtqacm4aDhN4zscMTAbc7cztz")

    assert 0 in cm._address_cache
    assert list(cm._address_cache[0].keys()) == [0, 1]
    assert len(cm._address_cache[0][0].keys()) == 3
    assert list(cm._address_cache[0][0].keys()) == [0, 1, 19]
    assert len(cm._address_cache[0][1].keys()) == 10

    assert cm.get_address(0, 0, 1) == "15hyvVXH2eJnakwhpqKBf5oTCa3o2bp8m8"
    assert cm.get_address(0, 0, 19) == "17TNXJSWjBdMpHAkSfuyfVKSvb3rLuWZqQ"
    assert cm.get_address(0, 1, 7) == "1FAqCWr2EkAz43JzPRsdqLKBQeLJo4Tc7M"

    chain_addrs = cm.get_addresses_for_chain(0, 0)
    assert len(chain_addrs) == 3
    for a in ["15qCydrcqURADXJHrtMW9m6SpPTa3kqkQb",
              "15hyvVXH2eJnakwhpqKBf5oTCa3o2bp8m8",
              "17TNXJSWjBdMpHAkSfuyfVKSvb3rLuWZqQ"]:
        assert a in chain_addrs

    chain_addrs = cm.get_addresses_for_chain(0, 1)
    assert len(chain_addrs) == 10

    assert cm.get_chain_indices(0, 0) == [0, 1, 19]
    assert cm.get_chain_indices(0, 1) == list(range(10))


def test_txns():
    txn = WalletTransaction.from_hex('01000000029ccb0665ec780f8b05bf2315a48dfb154dc41f91e8046a59f1c75656826dea5d000000006b483045022100f4d2161473f9d0ba4b5cdbc9e5b7b1d8fca32e3b6bede307352bef6aaa3a08cd022023d8444f78f69de6fd0f6cc391a7ca4de3dc4181220932d01511eb1129fee09e01210328bd51733a7d5bee05368680adef9aaa3f9bb716ec716d5896b1d80afb734d6cffffffff2424cb910235b2059d59023aecfebf6fce4eee31c637e9a0b350491849688727020000006a473044022072de3d707f98adfed3266e0261750cd7b5162732e525d7df17f4e55a55e953b902205046b597acf7acf41e725b459ba6cfe8c03a9d877375cdf483cab9620f92961101210291cbb1304614d86b15f4e8f39e9d8299cd0304ff8b81b5bcf6d9a6f32be649bbffffffff0240420f00000000001976a91434fe777d676fceb3509584c1d7b9f13ee56514d488ace05a0000000000001976a9145237ba33122495420711b3f2cc0463dbb24c9d3988ac00000000')  # nopep8

    txn.block = 374440
    txn.block_hash = Hash('0000000000000000038ee0066680705455d500f287f6c56db7a979c2426a4c02')
    txn.confirmations = 7533

    cm.insert_txn(txn)

    txid = "3779f27a81cdbc435ac258ce5076c211e7a953027aab42573b1b7ce9e50abe8e"
    assert txid in cm._txn_cache

    in_addrs = ["1DpCouKa2evX3f2aELUy7iNdsrYuLLaqWy",
                "1GcmBmvYWJKLFHxrTtx5DqQLV7oHQAkH2c"]

    out_addrs = [("15qCydrcqURADXJHrtMW9m6SpPTa3kqkQb", 1000000),
                 ("18VjAjZ7Au8U75LCHT7aH7mTwKETZwHTpi", 23264)]

    assert len(cm._txns_by_addr.keys()) == 4
    for i, a in enumerate(out_addrs):
        assert a[0] in cm._txns_by_addr
        assert list(cm._deposits_for_addr[a[0]][txid]) == [i]

    for i, a in enumerate(in_addrs):
        assert list(cm._spends_for_addr[a][txid]) == [i]

    # Check input and output caches
    assert txid in cm._inputs_cache
    assert len(cm._inputs_cache[txid]) == 2

    assert txid in cm._outputs_cache
    assert len(cm._outputs_cache[txid]) == 2
    assert cm._outputs_cache[txid][0]['output'] is not None
    assert cm._outputs_cache[txid][1]['output'] is not None
    assert cm._outputs_cache[txid][0]['status'] == CacheManager.UNSPENT
    assert cm._outputs_cache[txid][1]['status'] == CacheManager.UNSPENT

    out_txid1 = "5dea6d825656c7f1596a04e8911fc44d15fb8da41523bf058b0f78ec6506cb9c"
    assert out_txid1 in cm._outputs_cache
    assert cm._outputs_cache[out_txid1][0]['status'] == CacheManager.SPENT

    out_txid2 = "27876849184950b3a0e937c631ee4ece6fbffeec3a02599d05b2350291cb2424"
    assert out_txid2 in cm._outputs_cache
    assert len(cm._outputs_cache[out_txid2].keys()) == 1
    assert cm._outputs_cache[out_txid2][2]['status'] == CacheManager.SPENT

    assert cm.has_txns()
    assert cm.has_txns(0)
    assert not cm.has_txns(1)

    assert cm.have_transaction(txid)
    assert not cm.have_transaction(out_txid1)
    assert not cm.have_transaction(out_txid2)
    assert cm.get_transaction(txid) == txn
    assert cm.get_transaction(out_txid1) is None
    assert cm.get_transaction(out_txid2) is None

    # Check balances on addresses
    addr_balances = cm.get_balances([a[0] for a in out_addrs])
    for addr, exp_bal in out_addrs:
        assert addr_balances[addr] == exp_bal

    # Add a second transaction that deposits into addresses we have,
    # but insert it as unconfirmed
    txn_hex = "01000000028a9acc005a2158758e44242eee8c18fee7a43cda39a358cc783fb578cfa7cf5f000000006a47304402204a00fcb746f90095c1c50e048f1b0616b421617ca27a7a7465d4086a1623731802202404d0fce1b74f41ce1e3c63f61c8574c8cf2a5eae24ac4df714775168a9118c012102d8bfe3fd2d01f3a2b1380c34ccadcd318cafd1246f41258d7d244f409fb44c93ffffffff15857ef158778f603d34bcff74bd7935cb9d6b4a0147eea008be3f67bd395830020000006a4730440220466f93d784aa24bf497929433777fa283a7cd0000625179d3e9f5c75db4ad10f022022857a607665408a5521cbdf145c1fecd85c427ccf939c49f9a0d828a934e2530121021b5c9a9e6c97b4222c97da5a642e3531bce01b757cfdc9b29ac7d1cbf2d10710ffffffff0240420f00000000001976a91433a0a86dd9dab9902157d8d64e05fc8e0dfba16388ac7a1d0300000000001976a914134ca7427089b8f661efc9806a8418f72e57167f88ac00000000"  # nopep8

    txn = WalletTransaction.from_hex(txn_hex)
    cm.insert_txn(txn)

    txid = "d24f3b9f0aa7b6484bcea563f4c254bd24e8163906cbffc727c2b2dad43af61e"
    assert txid in cm._txn_cache

    in_addrs = ["1Ezv6YmYsZvALUaRcZRf8hBdxYni6cm78X",
                "16Mcvb7fYhif94d1RHCn5AE2dm1oXCGnH6"]

    out_addrs = [("15hyvVXH2eJnakwhpqKBf5oTCa3o2bp8m8", 1000000),
                 ("12m3fcaabUgYwWcodgVZUGH6ntFqVrHk5C", 204154)]

    for i, a in enumerate(out_addrs):
        assert a[0] in cm._txns_by_addr
        assert list(cm._deposits_for_addr[a[0]][txid]) == [i]

    for i, a in enumerate(in_addrs):
        assert list(cm._spends_for_addr[a][txid]) == [i]

    # Check input and output caches
    assert txid in cm._inputs_cache
    assert len(cm._inputs_cache[txid]) == 2

    assert txid in cm._outputs_cache
    assert cm._outputs_cache[txid][0]['output'] is not None
    assert cm._outputs_cache[txid][1]['output'] is not None
    assert cm._outputs_cache[txid][0]['status'] == CacheManager.UNSPENT | CacheManager.UNCONFIRMED
    assert cm._outputs_cache[txid][1]['status'] == CacheManager.UNSPENT | CacheManager.UNCONFIRMED

    out_txid1 = "5fcfa7cf78b53f78cc58a339da3ca4e7fe188cee2e24448e7558215a00cc9a8a"
    assert out_txid1 in cm._outputs_cache
    assert cm._outputs_cache[out_txid1][0]['status'] == CacheManager.SPENT | CacheManager.UNCONFIRMED

    out_txid2 = "305839bd673fbe08a0ee47014a6b9dcb3579bd74ffbc343d608f7758f17e8515"
    assert out_txid2 in cm._outputs_cache
    assert len(cm._outputs_cache[out_txid2].keys()) == 1
    assert cm._outputs_cache[out_txid2][2]['status'] == CacheManager.SPENT | CacheManager.UNCONFIRMED

    # Check that confirmed balances are 0 for the out_addrs
    out_a = [a[0] for a in out_addrs]
    conf_addr_balances = cm.get_balances(out_a)
    unconf_addr_balances = cm.get_balances(out_a, True)
    for addr, exp_bal in out_addrs:
        assert conf_addr_balances[addr] == 0
        assert unconf_addr_balances[addr] == exp_bal

    # Check utxos
    conf_addr_utxos = cm.get_utxos(out_a)
    unconf_addr_utxos = cm.get_utxos(out_a, True)
    for addr, exp_bal in out_addrs:
        assert addr not in conf_addr_utxos
        assert addr in unconf_addr_utxos
        assert len(unconf_addr_utxos[addr]) == 1
        utxo = unconf_addr_utxos[addr][0]
        assert utxo.value == exp_bal
        assert utxo.num_confirmations == 0

    # Reinsert the transaction with it as confirmed now
    txn = WalletTransaction.from_hex(txn_hex)
    txn.block = 374442
    txn.block_hash = Hash('000000000000000001de250dcfa47f8313aec2f1f41a56f4fb0d099eb497c2b2')
    txn.confirmations = 7684
    cm.insert_txn(txn)

    assert cm._outputs_cache[txid][0]['status'] == CacheManager.UNSPENT
    assert cm._outputs_cache[txid][1]['status'] == CacheManager.UNSPENT
    assert cm._outputs_cache[out_txid1][0]['status'] == CacheManager.SPENT
    assert cm._outputs_cache[out_txid2][2]['status'] == CacheManager.SPENT

    # Check the balances again
    conf_addr_balances = cm.get_balances(out_a)
    unconf_addr_balances = cm.get_balances(out_a, True)
    for addr, exp_bal in out_addrs:
        assert conf_addr_balances[addr] == exp_bal
        assert unconf_addr_balances[addr] == exp_bal

    # Check utxos again
    conf_addr_utxos = cm.get_utxos(out_a)
    unconf_addr_utxos = cm.get_utxos(out_a, True)
    for addr, exp_bal in out_addrs:
        assert addr in conf_addr_utxos
        assert addr in unconf_addr_utxos
        assert len(conf_addr_utxos[addr]) == 1
        assert len(unconf_addr_utxos[addr]) == 1
        utxo = conf_addr_utxos[addr][0]
        assert utxo.value == exp_bal
        assert utxo.num_confirmations == 7684

    # Insert a transaction that spends from one of the out addrs in
    # the above transactions.

    # 1. Insert it provisionally
    # 2. Re-insert as unconfirmed
    # 3. Re-insert as confirmed

    txn_hex = "01000000021ef63ad4dab2c227c7ffcb063916e824bd54c2f463a5ce4b48b6a70a9f3b4fd2000000006a473044022051008f06f1fc5783364712c7bf175c383ebb92c1001ba9f744f5170d5af00bb9022012baa83b3611b2c0e637d2f5e62dd3f6f4debfca805f8a42df6719a67614824d0121027fc10ccde9240463a86c983d2c8d1301311c9debf510119418b0da7b6fdb7ee7ffffffff8ebe0ae5e97c1b3b5742ab7a0253a9e711c27650ce58c25a43bccd817af27937000000006a473044022076fd5835628d4867b489c4c7afa885de33417a3536276b3f7066155b1bd79c15022030a218c2ca35b27e2beefb2298a0bf6fc9eabe93e07f388a1a3aee878025a7b6012102bed99adff9710dbc3e9f7966037d5824ffb134aeba70aec70e34e7eeb6547a94ffffffff0240420f00000000001976a914952e023bf19047e9a014af4ec067667695d8c99488acf8340f00000000001976a914743281d388add04da28e10a12af09c853f98609888ac00000000"  # nopep8

    txn = WalletTransaction.from_hex(txn_hex)

    # First test with a very short expiration
    cm.insert_txn(txn, mark_provisional=True, expiration=1)

    txid = "6fd3c96d466cd465b40e59be14d023c27f1d0ca13075119d3d6baeebfc587b8c"
    assert txid in cm._txn_cache
    assert cm._txn_cache[txid].provisional
    time.sleep(1.5)
    cm.prune_provisional_txns()
    assert txid not in cm._txn_cache

    # Now do default expiration
    cm.insert_txn(txn, mark_provisional=True)

    assert txid in cm._txn_cache

    in_addrs = ["15hyvVXH2eJnakwhpqKBf5oTCa3o2bp8m8",
                "15qCydrcqURADXJHrtMW9m6SpPTa3kqkQb"]

    out_addrs = [("1EbnoKrmUEe3hsK9gTVfgYAming6BuqM3L", 1000000),
                 ("1BbPtYsbBPFRCwnU5RuMTttraghXQ5JSZm", 996600)]

    for i, a in enumerate(out_addrs):
        assert a[0] in cm._txns_by_addr
        assert list(cm._deposits_for_addr[a[0]][txid]) == [i]

    for i, a in enumerate(in_addrs):
        assert list(cm._spends_for_addr[a][txid]) == [i]

    # Check input and output caches
    assert txid in cm._inputs_cache
    assert len(cm._inputs_cache[txid]) == 2

    assert txid in cm._outputs_cache
    assert cm._outputs_cache[txid][0]['output'] is not None
    assert cm._outputs_cache[txid][1]['output'] is not None
    assert cm._outputs_cache[txid][0]['status'] == CacheManager.UNSPENT | CacheManager.PROVISIONAL | CacheManager.UNCONFIRMED  # nopep8
    assert cm._outputs_cache[txid][1]['status'] == CacheManager.UNSPENT | CacheManager.PROVISIONAL | CacheManager.UNCONFIRMED  # nopep8

    out_txid1 = "d24f3b9f0aa7b6484bcea563f4c254bd24e8163906cbffc727c2b2dad43af61e"
    assert out_txid1 in cm._outputs_cache
    assert cm._outputs_cache[out_txid1][0]['status'] == CacheManager.SPENT | CacheManager.PROVISIONAL | CacheManager.UNCONFIRMED  # nopep8

    out_txid2 = "3779f27a81cdbc435ac258ce5076c211e7a953027aab42573b1b7ce9e50abe8e"
    assert out_txid2 in cm._outputs_cache
    assert len(cm._outputs_cache[out_txid2].keys()) == 2
    assert cm._outputs_cache[out_txid2][0]['status'] == CacheManager.SPENT | CacheManager.PROVISIONAL | CacheManager.UNCONFIRMED  # nopep8

    # Check that confirmed balances are 0 for the out_addrs
    out_a = [a[0] for a in out_addrs]
    conf_addr_balances = cm.get_balances(out_a)
    unconf_addr_balances = cm.get_balances(out_a, True)
    for addr, exp_bal in out_addrs:
        assert conf_addr_balances[addr] == 0
        assert unconf_addr_balances[addr] == exp_bal

    # Check utxos
    conf_addr_utxos = cm.get_utxos(out_a)
    unconf_addr_utxos = cm.get_utxos(out_a, True)
    for addr, exp_bal in out_addrs:
        assert addr not in conf_addr_utxos
        assert addr in unconf_addr_utxos
        assert len(unconf_addr_utxos[addr]) == 1
        utxo = unconf_addr_utxos[addr][0]
        assert utxo.value == exp_bal
        assert utxo.num_confirmations == 0

    # Re-insert as unconfirmed
    txn = WalletTransaction.from_hex(txn_hex)
    cm.insert_txn(txn, mark_provisional=False)

    # Only the statuses should change, so check those.
    assert cm._outputs_cache[txid][0]['status'] == CacheManager.UNSPENT | CacheManager.UNCONFIRMED
    assert cm._outputs_cache[txid][1]['status'] == CacheManager.UNSPENT | CacheManager.UNCONFIRMED
    assert cm._outputs_cache[out_txid1][0]['status'] == CacheManager.SPENT | CacheManager.UNCONFIRMED
    assert cm._outputs_cache[out_txid2][0]['status'] == CacheManager.SPENT | CacheManager.UNCONFIRMED

    # Re-insert as confirmed
    txn = WalletTransaction.from_hex(txn_hex)
    txn.block = 374445
    txn.block_hash = Hash("000000000000000004c241778cbbc269e912df5fe8d856efaea916daa82d2575")
    txn.confirmations = 7781
    cm.insert_txn(txn, mark_provisional=False)

    # Only the statuses should change, so check those.
    assert cm._outputs_cache[txid][0]['status'] == CacheManager.UNSPENT
    assert cm._outputs_cache[txid][1]['status'] == CacheManager.UNSPENT
    assert cm._outputs_cache[out_txid1][0]['status'] == CacheManager.SPENT
    assert cm._outputs_cache[out_txid2][0]['status'] == CacheManager.SPENT

    # Check balances
    out_a = [a[0] for a in out_addrs]
    conf_addr_balances = cm.get_balances(out_a)
    unconf_addr_balances = cm.get_balances(out_a, True)
    for addr, exp_bal in out_addrs:
        assert conf_addr_balances[addr] == exp_bal
        assert unconf_addr_balances[addr] == exp_bal

    # Check utxos
    conf_addr_utxos = cm.get_utxos(out_a)
    unconf_addr_utxos = cm.get_utxos(out_a, True)
    for addr, exp_bal in out_addrs:
        assert addr in conf_addr_utxos
        assert addr in unconf_addr_utxos
        assert len(unconf_addr_utxos[addr]) == 1
        utxo = conf_addr_utxos[addr][0]
        assert utxo.value == exp_bal
        assert utxo.num_confirmations == 7781

    # Check utxos for all addresses that have deposits - we should only have 4
    addrs = ["1DpCouKa2evX3f2aELUy7iNdsrYuLLaqWy",
             "1GcmBmvYWJKLFHxrTtx5DqQLV7oHQAkH2c",
             "15hyvVXH2eJnakwhpqKBf5oTCa3o2bp8m8",
             "15qCydrcqURADXJHrtMW9m6SpPTa3kqkQb",
             "1EbnoKrmUEe3hsK9gTVfgYAming6BuqM3L",
             "1BbPtYsbBPFRCwnU5RuMTttraghXQ5JSZm",
             "1Ezv6YmYsZvALUaRcZRf8hBdxYni6cm78X",
             "16Mcvb7fYhif94d1RHCn5AE2dm1oXCGnH6",
             "12m3fcaabUgYwWcodgVZUGH6ntFqVrHk5C",
             "18VjAjZ7Au8U75LCHT7aH7mTwKETZwHTpi"]

    conf_utxos = cm.get_utxos(addrs)
    assert len(conf_utxos) == 4
    utxo_addrs_values = [("18VjAjZ7Au8U75LCHT7aH7mTwKETZwHTpi", 23264),
                         ("12m3fcaabUgYwWcodgVZUGH6ntFqVrHk5C", 204154),
                         ("1EbnoKrmUEe3hsK9gTVfgYAming6BuqM3L", 1000000),
                         ("1BbPtYsbBPFRCwnU5RuMTttraghXQ5JSZm", 996600)]

    for a, value in utxo_addrs_values:
        assert a in conf_utxos
        assert len(conf_utxos[a]) == 1
        assert conf_utxos[a][0].value == value

    assert "15hyvVXH2eJnakwhpqKBf5oTCa3o2bp8m8" not in conf_utxos
    assert "15qCydrcqURADXJHrtMW9m6SpPTa3kqkQb" not in conf_utxos

    # Now delete the last transaction
    cm._delete_txn(txid)

    assert txid not in cm._txn_cache
    assert txid not in cm._inputs_cache
    assert txid not in cm._outputs_cache

    for in_addr in in_addrs:
        assert in_addr not in cm._spends_for_addr

    for out_addr, _ in out_addrs:
        assert out_addr not in cm._deposits_for_addr

    for out_txid, index in [(out_txid1, 0), (out_txid2, 0)]:
        out = cm._outputs_cache[out_txid][index]
        assert out['status'] == CacheManager.UNSPENT
        assert out['spend_txid'] is None
        assert out['spend_index'] is None


def test_whole(cache, exp_conf_balance, exp_unconf_balance):
    cm = CacheManager()
    # Don't prune for testing purposes
    cm.load_from_dict(cache, prune_provisional=False)

    addrs = cm.get_addresses_for_chain(0x80000000, 0) + \
        cm.get_addresses_for_chain(0x80000000, 1)

    conf_balances = cm.get_balances(addrs)
    unconf_balances = cm.get_balances(addrs, True)

    conf_balance = sum([v for k, v in conf_balances.items()])
    unconf_balance = sum([v for k, v in unconf_balances.items()])

    assert conf_balance == exp_conf_balance
    assert unconf_balance == exp_unconf_balance
