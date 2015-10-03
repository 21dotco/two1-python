import gzip
import inspect
import json
import os
import pytest

this_file_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

def pytest_generate_tests(metafunc):
    _blocks = []
    _txns = []
    _txns_dict = {}
    with gzip.open(os.path.join(this_file_path, "txns.json.gz"), 'rt') as f:
        _txns = json.load(f)

    # Create a dict keyed by the txn hash so that we can populate the
    # blocks with it. This assumes that all the txns for each of the
    # blocks in blocks.json are in txns.json. If these files were
    # created by gen_test_inputs.py, that will be the case.
    for t, txn in enumerate(_txns):
        _txns_dict[txn['hash']] = txn
        
    with gzip.open(os.path.join(this_file_path, "blocks.json.gz"), 'rt') as f:
        _blocks = json.load(f)

    # Populate blocks with their txns.
    for b in _blocks:
        block_txns = []
        for t in b['transaction_hashes']:
            block_txns.append(_txns_dict.get(t, None))
        
        b['transactions'] = block_txns
        
    if 'block_json' in metafunc.fixturenames:
        metafunc.parametrize("block_json", _blocks)
    if 'txn_json' in metafunc.fixturenames:
        metafunc.parametrize("txn_json", _txns)
