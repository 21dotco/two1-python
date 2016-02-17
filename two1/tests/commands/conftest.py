# standard python imports
import unittest.mock as mock

# 3rd party imports
import pytest

# two1 imports
# naming module doc so theres not a conflict with the fixture name
from two1.commands import doctor as doc


@pytest.fixture()
def config():
    return mock.Mock()

@pytest.fixture()
def doctor(config):
    return doc.Doctor(config)

