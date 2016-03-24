""" Unit test to verify update command """
# standard python imports
import subprocess
import datetime
import urllib
import unittest.mock as mock
import sys

# 3rd party imports
import requests
import click
import pytest

# two1 imports
import two1
import two1.commands.update as update
import two1.commands.util.exceptions as exceptions
import two1.commands.util.uxstring as uxstring


@pytest.mark.parametrize("timedelta_kwargs, outcome", [
    # simple case of last updated was today
    (dict(days=0), True),

    # Updated yesterday
    (dict(days=-1), False),

    # Updated in the future!
    (dict(days=1), True),
    ])
def test_check_for_an_update_today(mock_config, timedelta_kwargs, outcome):
    last_updated = datetime.datetime.today() + datetime.timedelta(**timedelta_kwargs)
    mock_config.last_update_check = datetime.datetime.strftime(last_updated, "%Y-%m-%d")
    assert update.checked_for_an_update_today(mock_config) == outcome


@mock.patch("two1.commands.update.checked_for_an_update_today", return_value=False)
@pytest.mark.parametrize("pypi_version, two1_version, should_update, apt_update, in_venv", [
    # update occurs for apt
    ("1.0.0", "0.1.0", True, True, None),

    # update occurs for pip not in a venv
    ("1.0.0", "0.1.0", True, False, False),

    # update occurs for pip in a venv
    ("1.0.0", "0.1.0", True, False, True),

    # update does NOT occur at all because pypi version is less than two1_version
    ("0.0.1", "1.0.0", False, None, None),
    ])
def test_update(mock_config, two1_version_reset, two1_version, should_update, pypi_version, apt_update, in_venv):
    two1.TWO1_VERSION = two1_version

    with mock.patch("two1.commands.update.lookup_pypi_version", return_value=pypi_version), \
         mock.patch("two1.commands.update.subprocess") as mock_subprocess, \
         mock.patch("two1.commands.update.os.path.isdir", return_value=apt_update), \
         mock.patch("two1.commands.update.checked_for_an_update_today", return_value=False):

        # only care about checking for venv when doing pip based update
        if apt_update is False:
            if in_venv:
                sys.real_prefix=True
            else:
                if hasattr(sys, "real_prefix"):
                    del sys.real_prefix

        update._update(mock_config, None)

        if should_update:
            # check for the apt specific update calls
            if apt_update:
                mock_subprocess.check_call.assert_any_call(["sudo", "apt-get", "update"])
                mock_subprocess.check_call.assert_called_with([
                    "sudo",
                    "apt-get",
                    "-y",
                    "install",
                    "--only-upgrade",
                    "two1={}-1".format(pypi_version),
                    "minerd",
                    "zerotier-one"])
            else:
                pip_install_str = "pip3 install -i {}/pypi -U --no-deps -I two1=={}".format(two1.TWO1_PYPI_HOST, pypi_version)
                if not in_venv:
                    pip_install_str = "sudo {}".format(pip_install_str)

                mock_subprocess.check_call.assert_called_once_with(pip_install_str.split(' '))
        else:
            # if an update is NOT happening make sure no update calls occured
            mock_subprocess.check_call.assert_not_called()


def test_two1_version_error(patch_click, two1_version_reset, mock_config):
    """ This test makes sure that a Two1Error is raised when two1.TWO1_VERSION is set """
    two1.TWO1_VERSION = ""
    with pytest.raises(exceptions.Two1Error) as ex:
        update._update(mock_config, None)

    assert ex.value._msg == uxstring.UxString.Error.version_not_detected


@pytest.mark.parametrize("side_effect, mock_json, error_string", [
    # check to make sure request connection errors are handled
    (requests.exceptions.Timeout, None, uxstring.UxString.Error.update_server_connection),
    (requests.exceptions.ConnectionError, None, uxstring.UxString.Error.update_server_connection),

    # check to make sure invalid json from the server is handled
    (None, mock.Mock(side_effect=ValueError), uxstring.UxString.Error.version_not_found),
    (None, mock.Mock(return_value={"json": "without pakages"}), uxstring.UxString.Error.version_not_found),
    (None, mock.Mock(return_value={"packages": [{"json": "without version"}]}), uxstring.UxString.Error.version_not_found),
    ])
def test_lookup_pypi_version_errors(mock_config, side_effect, mock_json, error_string):
    with mock.patch("two1.commands.update.requests.get") as mock_get:
        # side effect will raise an exception during the get request
        mock_get.side_effect = side_effect

        # set up mock response from get call
        mock_response = mock.Mock()
        mock_response.json = mock_json

        # get return value is a mock
        mock_get.return_value = mock_response

        with pytest.raises(exceptions.Two1Error) as ex:
            update.lookup_pypi_version()

        assert ex.value._msg == error_string
