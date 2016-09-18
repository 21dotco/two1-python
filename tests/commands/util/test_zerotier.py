""" Unit tests for the zerotier utility

    Every test in this module uses parametrization to test various inputs
    and outcomes.
"""
# standard python imports
import unittest.mock as mock
import json

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
@mock.patch('two1.commands.util.zerotier.is_installed')
def test_cli(is_installed_mock, args, outcome):
    """ Simple test to check input params

        We do not want to test ALL zerotier commands here. This test is
        specifically checking the zerotier.cli() funciton and NOT the
        zerotier cli output.
    """
    is_installed_mock.return_value = True
    with mock.patch('two1.commands.util.zerotier.subprocess.check_output'):
        if outcome is None:
            zerotier.cli(args)
        else:
            with pytest.raises(outcome):
                zerotier.cli(args)


@pytest.mark.parametrize("args, outcome", [
    (None, ValueError),
    ((), ValueError),
    (("sheep"), {"test": "dict"}),
    ("goat", {"test": "dict"}),
    (("sheep"), '{"test":None}'.encode()),
    ])
@mock.patch('two1.commands.util.zerotier.is_installed')
def test_cli_json(is_installed_mock, args, outcome):
    """ Simple test to check input params and json results

        Mock zerotier.cli to return a fake json respose from zerotier-cli.
    """
    is_installed_mock.return_value = True
    # expecting valid output from zerotier.cli
    if isinstance(outcome, dict):
        cli_return_value = json.dumps(outcome).encode()
        with mock.patch("two1.commands.util.zerotier.cli", return_value=cli_return_value):
            assert zerotier.cli_json(args) == outcome

    # expecting JSONError when string is given as an outcome
    elif isinstance(outcome, bytes):
        with pytest.raises(ValueError):
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
    ("False", "False", False),  # fault tolerant inputs
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
        "name": "21mkt",
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
        "name": "21mkt",
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
    (MULTIPLE_NETWORKS, {'21mkt': "10.244.223.250", '': ""}),
    (SINGLE_NETWORKS, {'21mkt': "10.244.223.250"}),
    (EMPTY_NETWORKS, {}),
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
    ("21mkt", {'21mkt': "10.244.223.250", '': ""}, "10.244.223.250"),
    ("21mkt", {'21beta': "10.244.223.250", '': ""}, None),
    ("", {'21mkt': "10.244.223.250"}, None),
    ("", {'21mkt': "10.244.223.250", '': "10.244.223.250"}, "10.244.223.250"),
    ("21mkt", {}, None)
    ])
def test_get_address(network_name, get_all_ret_val, outcome):
    """ Tests zerotier.get_address function """
    with mock.patch("two1.commands.util.zerotier.get_all_addresses",
                    return_value=get_all_ret_val):
        assert zerotier.get_address(network_name) == outcome


@mock.patch('two1.commands.util.zerotier.cli_json')
def test_info(mock_cli_json):
    """ Makes sure that the return value is a dict """
    mock_cli_json.return_value = [("test", True)]
    assert zerotier.info() == {"test": True}


@mock.patch('two1.commands.util.zerotier.cli_json')
def test_list_networks(mock_cli_json):
    """ Makes sure that the return value is a dict """
    mock_cli_json.return_value = "test"
    assert zerotier.list_networks() == "test"


@mock.patch('two1.commands.util.zerotier.cli_json')
def test_list_peers(mock_cli_json):
    """ Makes sure that the return value is a dict """
    mock_cli_json.return_value = "test"
    assert zerotier.list_peers() == "test"


@pytest.mark.parametrize("info_dict, outcome", [
    ({"address": "0123456789"}, "0123456789"),
    ({"address": "0123456789abcdef"}, ValueError)
    ])
def test_device_address(info_dict, outcome):
    """ Ensures that a ValueError is reaised on invalid id """
    with mock.patch("two1.commands.util.zerotier.info") as info_mock:
        info_mock.return_value = info_dict

        if isinstance(outcome, str):
            assert zerotier.device_address() == outcome
        else:
            with pytest.raises(outcome):
                zerotier.device_address()


@pytest.mark.parametrize("network_id, outcome", [
    ("0123456789", ValueError),
    ("0123456789abcdef", "return_value")
    ])
@mock.patch('two1.commands.util.zerotier.cli')
def test_join_network(mock_cli, network_id, outcome):
    """ Ensures that a ValueError is reaised on invalid id """
    if isinstance(outcome, str):
        mock_cli.return_value = outcome
        assert zerotier.join_network(network_id) == outcome
    else:
        with pytest.raises(outcome):
            zerotier.join_network(network_id)


@pytest.mark.parametrize("network_id, outcome", [
    ("0123456789", ValueError),
    ("0123456789abcdef", "return_value")
    ])
@mock.patch('two1.commands.util.zerotier.cli')
def test_leave_network(mock_cli, network_id, outcome):
    """ Ensures that a ValueError is reaised on invalid id """
    if isinstance(outcome, str):
        mock_cli.return_value = outcome
        assert zerotier.leave_network(network_id) == outcome
    else:
        with pytest.raises(outcome):
            zerotier.leave_network(network_id)


@pytest.mark.parametrize("which_side_effect, system_return_value, cmd, outcome", [
    ((None, None), "Windows", (), EnvironmentError),
    (("yep", None), "Linux", ('sudo', 'systemctl', 'start', 'zerotier-one.service'), 0),
    ((None, "yep"), "Linux", ('sudo', 'service', 'zerotier-one', 'start'), 0),
    ((None, None), "Linux", (), EnvironmentError),
    ((None, None), "Darwin", (), ""),
    ])
@mock.patch('two1.commands.util.zerotier.subprocess.call')
@mock.patch('two1.commands.util.zerotier.platform.system')
@mock.patch('two1.commands.util.zerotier.shutil.which')
@mock.patch('two1.commands.util.zerotier.is_installed')
def test_start_daemon(
        is_installed_mock, which_mock, system_mock, check_output_mock,
        which_side_effect, system_return_value, cmd, outcome):
    """ Tests various platforms and sytem configs if the daemon can be started """
    which_mock.side_effect = which_side_effect
    system_mock.return_value = system_return_value
    is_installed_mock.return_value = True

    if isinstance(outcome, (str, int)):
        check_output_mock.return_value = outcome
        assert zerotier.start_daemon() == outcome
        if outcome:
            check_output_mock.assert_called_once_with(cmd)
    else:
        check_output_mock.side_effect = outcome
        with pytest.raises(outcome):
            zerotier.start_daemon()
