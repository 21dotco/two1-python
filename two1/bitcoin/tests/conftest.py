import inspect
import json
import os
import pytest

this_file_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))

def pytest_generate_tests(metafunc):
    if 'block_json' in metafunc.fixturenames:
        _blocks = []
        with open(os.path.join(this_file_path, "blocks.json"), 'r') as f:
            _blocks = json.load(f)

        metafunc.parametrize("block_json", _blocks)
    if 'txn_json' in metafunc.fixturenames:
        _txns = []
        with open(os.path.join(this_file_path, "txns.json"), 'r') as f:
            _txns = json.load(f)

        metafunc.parametrize("txn_json", _txns)
