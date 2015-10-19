from datetime import datetime
from datetime import timedelta
from unittest.mock import MagicMock
from urllib.parse import urljoin
import subprocess

from collections import namedtuple
import pytest
import responses
from two1.commands.exceptions import ServerRequestError
from two1.commands.update import checked_for_an_update_today
from two1.commands.update import update_two1_package
from two1.commands import update, config


class MockConfig(object):
    def __init__(self):
        self.last_update_check = None

    def update_key(self, k, v):
        if k == 'last_update_check':
            self.last_update_check = v
        else:
            raise AttributeError

    def save(self):
        pass


def test_check_for_an_update_today():
    c = namedtuple('Config', ['blah'])

    # This should return false as the config is missing the attribute.
    assert not checked_for_an_update_today(c)

    c = MockConfig()
    today = datetime.today()
    yesterday = today - timedelta(days=1)
    c.last_update_check = yesterday.date().strftime("%Y-%m-%d")
    assert not checked_for_an_update_today(c)

    c.last_update_check = today.date().strftime("%Y-%m-%d")
    assert checked_for_an_update_today(c)

    # What happens if it's tomorrow?
    tomorrow = today + timedelta(days=1)
    c.last_update_check = tomorrow.date().strftime("%Y-%m-%d")
    assert checked_for_an_update_today(c)


@responses.activate
def test_update_two1_package():
    c = MockConfig()
    v = 'latest'

    today = datetime.today()
    yesterday = today - timedelta(days=1)
    c.last_update_check = today.date().strftime("%Y-%m-%d")
    rv = update_two1_package(c, v)

    assert not rv['update_available']
    assert rv['update_successful'] is None

    url = urljoin(config.TWO1_PYPI_HOST, "api/package/{}/".format(config.TWO1_PACKAGE_NAME))
    c.last_update_check = yesterday.date().strftime("%Y-%m-%d")
    responses.add(responses.GET, url,
                  body='{"error": "not found"}', status=404,
                  content_type='application/json')
    with pytest.raises(ServerRequestError):
        rv = update_two1_package(c, v)

    json = """{"write": false, "packages": [{"url": "https://dotco-pypi.s3.amazonaws.com/0905/two1/two1-0.2.2.tar.gz?Signature=TGAuN2hzXPSqiIqKeoI7I8ZcCEk%3D&Expires=1443810441&AWSAccessKeyId=AKIAJ2NYFHIGZ7M62AEA", "last_modified": 1443412967.216141, "name": "two1", "version": "0.2.2", "filename": "two1-0.2.2.tar.gz"}, {"url": "https://dotco-pypi.s3.amazonaws.com/5a77/two1/two1-0.2.1.tar.gz?Signature=A5IPrSUBbabbKXrN5V65BfQHpXM%3D&Expires=1443810441&AWSAccessKeyId=AKIAJ2NYFHIGZ7M62AEA", "last_modified": 1443136403.0, "name": "two1", "version": "0.2.1", "filename": "two1-0.2.1.tar.gz"}]}"""

    # Reset last_update_check
    c.last_update_check = yesterday.date().strftime("%Y-%m-%d")
    update.TWO1_VERSION = "5.3.0"  # This should be safe to not trigger an update
    responses.reset()
    responses.add(responses.GET, url, body=json, status=200)

    rv = update_two1_package(c, v)
    assert c.last_update_check == today.date().strftime("%Y-%m-%d")
    assert not rv['update_available']
    assert rv['update_successful'] is None

    # Now let's try an update
    update.TWO1_VERSION = "0.0.1"  # Should be safe to always trigger an update
    c.last_update_check = yesterday.date().strftime("%Y-%m-%d")
    subprocess.check_call = MagicMock(return_value=True)

    rv = update_two1_package(c, v)
    assert c.last_update_check == today.date().strftime("%Y-%m-%d")
    assert rv['update_available']
    assert rv['update_successful']

    # Test where subprocess.check_call raises an error
    c.last_update_check = yesterday.date().strftime("%Y-%m-%d")
    subprocess.check_call = MagicMock(side_effect=subprocess.CalledProcessError("foo", "bar"))

    rv = update_two1_package(c, v)
    assert c.last_update_check == today.date().strftime("%Y-%m-%d")
    assert rv['update_available']
    assert not rv['update_successful']
