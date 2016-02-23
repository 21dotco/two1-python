""" Unit tests for the zerotier utility

    The simple functions which call zerotier.cli or zoertier.cli_json
    under the hood are not tested because the base functions are tested.
    We do not want to get into the bussiness of testing zerotiers cli
    for proper output.

    Every test in this module uses parametrization to test various inputs
    and outcomes.
"""
# standard python imports
import unittest.mock as mock
import json
import subprocess

# 3rd party imports
import pytest

# two1 imports
import two1.commands.util.zerotier as zerotier


@pytest.mark.parametrize("mock_return_value, outcome", [
    (True, True),
    (None, False)])
def test_is_installed(mock_return_value, outcome):
    """ Simple test to ensure proper values are returned from is_installed """
    with mock.patch("two1.commands.util.zerotier.shutil.which", return_value=mock_return_value):
        assert zerotier.is_installed() == outcome


@pytest.mark.parametrize("args, outcome", [
    (None, ValueError),
    ((), ValueError),
    (("sheep"), None),
    ("goat", None)])
def test_cli(args, outcome):
    """ Simple test to check input params

        We do not want to test ALL zerotier commands here. This test is
        specifically checking the zerotier.cli() funciton and NOT the
        zerotier cli output.
    """
    with mock.patch('two1.commands.util.zerotier.subprocess.check_output'):
        if outcome is None:
            zerotier.cli(args)
        else:
            with pytest.raises(outcome):
                zerotier.cli(args)


@pytest.mark.parametrize("args, outcome", [
    (None, ValueError),
    ((), ValueError),
    (("sheep"), {"test":"dict"}),
    ("goat", {"test":"dict"}),
    (("sheep"), '{"test":None}'.encode()),
    ])
def test_cli_json(args, outcome):
    """ Simple test to check input params and json results

        Mock zerotier.cli to return a fake json respose from zerotier-cli.
    """
    # expecting valid output from zerotier.cli
    if isinstance(outcome, dict):
        cli_return_value = json.dumps(outcome).encode()
        with mock.patch("two1.commands.util.zerotier.cli", return_value=cli_return_value):
            assert zerotier.cli_json(args) == outcome

    # expecting JSONError when string is given as an outcome
    elif isinstance(outcome, bytes):
        with pytest.raises(json.decoder.JSONDecodeError):
            with mock.patch("two1.commands.util.zerotier.cli", return_value=outcome):
                zerotier.cli_json(args)

    # expecting an exception because of bad input args
    else:
        with pytest.raises(outcome):
            zerotier.cli_json(args)


@pytest.mark.parametrize("id_str, id_len, outcome", [
    ("0123456789abcdef", 16, True),
    ("0123456789ABCDEF", 16, True),
    ("0123456789", 16, False),
    ("0123456789ABCDEF", 10, False),
    ("False", 16, False),
    ("False", "False", False), #fault tolerant inputs
    ("", 0, False),
    ("1", 1, True),
    ])
def test_is_valid(id_str, id_len, outcome):
    """ Test to verify zerotier.is_valid handles various inputs """
    assert zerotier.is_valid(id_str, id_len) == outcome


MULTIPLE_NETWORKS = [
    {
        "nwid": "6c0c6960a20bf150",
        "mac": "32:07:df:07:02:6d",
        "name": "21market",
        "status": "OK",
        "type": "PRIVATE",
        "assignedAddresses": ["10.244.223.250/16"],
        "portDeviceName": "zt0"
    },
    {
        "nwid": "6c0c6369a283ca29",
        "mac": "06:8c:77:07:02:6d",
        "name": "",
        "status": "REQUESTING_CONFIGURATION",
        "type": "PRIVATE",
        "assignedAddresses": [],
        "portDeviceName": "zt1"
    }
]

SINGLE_NETWORKS = [
    {
        "nwid": "6c0c6960a20bf150",
        "mac": "32:07:df:07:02:6d",
        "name": "21market",
        "status": "OK",
        "type": "PRIVATE",
        "assignedAddresses": ["10.244.223.250/16"],
        "portDeviceName": "zt0"
    }
]

EMPTY_NETWORKS = []


@pytest.mark.parametrize("network_id, list_networks_ret_val, outcome", [
    ("6c0c6960a20bf150", MULTIPLE_NETWORKS, ["10.244.223.250", "16"]),
    ("not a valid str", MULTIPLE_NETWORKS, RuntimeError),
    ("6c0c6369a283ca29", MULTIPLE_NETWORKS, RuntimeError),
    # Cannot have multiple networks and not give a network_id
    (None, MULTIPLE_NETWORKS, RuntimeError),

    ("6c0c6960a20bf150", SINGLE_NETWORKS, ["10.244.223.250", "16"]),
    ("not a valid str", SINGLE_NETWORKS, RuntimeError),
    (None, SINGLE_NETWORKS, RuntimeError),

    (None, EMPTY_NETWORKS, RuntimeError),
    ])
def test_get_address_by_id(network_id, list_networks_ret_val, outcome):
    """ Tests zerotier.get_address_by_id """
    with mock.patch("two1.commands.util.zerotier.list_networks",
                    return_value=list_networks_ret_val):

        if isinstance(outcome, list):
            assert zerotier.get_address_by_id(network_id) == outcome
        else:
            with pytest.raises(outcome):
                zerotier.get_address_by_id(network_id)


@pytest.mark.parametrize("list_networks_ret_val, outcome", [
    (MULTIPLE_NETWORKS, {'21market': "10.244.223.250", '': ""}),
    (SINGLE_NETWORKS, {'21market': "10.244.223.250"}),
    (EMPTY_NETWORKS, {}),
    (ValueError, {})
    ])
def test_get_all_addresses(list_networks_ret_val, outcome):
    """ Tests zerotier.get_all_addresses function """
    with mock.patch("two1.commands.util.zerotier.list_networks") as mock_list_networks:
        if isinstance(list_networks_ret_val, list):
            mock_list_networks.return_value = list_networks_ret_val
        else:
            mock_list_networks.side_effect = list_networks_ret_val

        assert zerotier.get_all_addresses() == outcome


@pytest.mark.parametrize("network_name, get_all_ret_val,  outcome", [
    ("21market", {'21market': "10.244.223.250", '': ""}, "10.244.223.250"),
    ("21market", {'21beta': "10.244.223.250", '': ""}, None),
    ("", {'21market': "10.244.223.250"}, None),
    ("", {'21market': "10.244.223.250", '': "10.244.223.250"}, "10.244.223.250"),
    ("21market", {}, None)
    ])
def test_get_address(network_name, get_all_ret_val, outcome):
    """ Tests zerotier.get_address function """
    with mock.patch("two1.commands.util.zerotier.get_all_addresses",
                    return_value=get_all_ret_val):
        assert zerotier.get_address(network_name) == outcome

