import gzip
import inspect
import json
import os


this_file_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


def pytest_generate_tests(metafunc):
    c = []

    tests = [("prod_wallet_cache.json.gz", 77831046, 77828046),
             ("wallet_6565716f_cache.json.unconf_deposit", 3640200, 3662900),
             ("wallet_59554c44_cache.json.unconf_chain_spends", 2846200, 2335200)]
    for t in tests:
        path = os.path.join(this_file_path, t[0])
        if os.path.exists(path):
            if path.endswith(".gz"):
                with gzip.open(path, 'rt') as f:
                    cache = json.load(f)
            else:
                with open(path) as f:
                    cache = json.load(f)

            c.append((cache, t[1], t[2]))

    if 'cache' in metafunc.fixturenames and \
       'exp_conf_balance' in metafunc.fixturenames:
        metafunc.parametrize("cache, exp_conf_balance, exp_unconf_balance", c)
