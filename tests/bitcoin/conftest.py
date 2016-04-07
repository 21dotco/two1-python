import gzip
import inspect
import json
import os
import pytest

this_file_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))


@pytest.fixture(scope="session")
def txns_json():
    with gzip.open(os.path.join(this_file_path, "txns.json.gz"), 'rt') as f:
        _txns = json.load(f)

    return _txns


@pytest.fixture(scope="session")
def blocks_json(txns_json):
    _blocks = []
    _txns = txns_json
    _txns_dict = {}

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

    return _blocks
