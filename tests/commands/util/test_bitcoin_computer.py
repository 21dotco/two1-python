# standard python imports
import unittest.mock as mock
import builtins
import json
import socket

# 3rd party imports
import pytest

# two1 imorts
from two1.commands.util import bitcoin_computer

# String to use as the content of the mocked file
UUID_STR = "12345678-1234-1234-1234-123456789012"


@pytest.mark.parametrize("mock_file, side_effect, outcome", [
    # Checks is get_uuid() strips the null byte
    (mock.mock_open(read_data="{}\x00".format(UUID_STR)), None, UUID_STR),
    # Just regular uuid string no null byte
    (mock.mock_open(read_data="{}".format(UUID_STR)), None, UUID_STR),
    # Blank file
    (mock.mock_open(read_data=""), None, None),
    # File not there
    (mock.mock_open(), FileNotFoundError, None)])
def test_get_uuid(mock_file, side_effect, outcome):
    """ Mocks the builtin open function to test various outcomes of opening and reading the uuid file """
    with mock.patch.object(builtins, "open", mock_file) as open_mock:
        open_mock.side_effect = side_effect
        assert bitcoin_computer.get_device_uuid() == outcome


@pytest.mark.parametrize("mock_file, side_effect, outcome", [
    # Check product file for valid content
    (mock.mock_open(read_data="21 Bitcoin Computer"), None, True),
    # Check product file for invalid content
    (mock.mock_open(read_data="donkey"), None, False),
    # Check product file for invalid content
    (mock.mock_open(read_data="21 "), None, False),
    # Blank file
    (mock.mock_open(read_data=""), None, False),
    # File not there
    (mock.mock_open(), FileNotFoundError, False)])
def test_has_mining_asic(mock_file, side_effect, outcome):
    """ Mocks the builtin open function to test various outcomes of opening and reading the product file """
    with mock.patch.object(builtins, "open", mock_file) as open_mock:
        open_mock.side_effect = side_effect
        assert bitcoin_computer.has_mining_chip() == outcome


HASHRATE = 50*1e9
STAT_EVENT_STARTING_UP = {
    'timestamp': 1455844537.719672,
    'type': 'StatisticsEvent',
    'payload': {
        'statistics': {
            'hashrate': {
                '60min': HASHRATE,
                '15min': HASHRATE,
                '5min': HASHRATE
                },
            # 60 seconds is not enough uptime
            'uptime': 90}
        }
    }

STAT_EVENT_HASHRATE = {
    'timestamp': 1455844537.719672,
    'type': 'StatisticsEvent',
    'payload': {
        'statistics': {
            'hashrate': {
                '60min': HASHRATE,
                '15min': HASHRATE,
                '5min': HASHRATE
                },
            # 61 minutes is enough uptime
            'uptime': (61*60)
            }
        }
    }

NETWORK_EVENT = {
    "payload": {
        "url": "dummy://16.0",
        "message": "Connected to dummy.",
        "username": None,
        "connected": True,
        },
    "type": "NetworkEvent",
    "timestamp": 1455844282.4812388
    }


@pytest.mark.parametrize("event_dicts, side_effect, outcome", [
    ([NETWORK_EVENT, STAT_EVENT_HASHRATE], None, HASHRATE),
    ([NETWORK_EVENT, STAT_EVENT_STARTING_UP], None, -1),
    ([NETWORK_EVENT], None, TimeoutError),
    ([], None, TimeoutError),
    (None, None, TimeoutError),
    ([], socket.timeout, TimeoutError),
    ])
@mock.patch.object(bitcoin_computer.socket.socket, "connect")
def test_get_hashrate(mock_connect, event_dicts, side_effect, outcome):
    """ Mocks socket.recv function to test various payloads while getting hashrate """
    if event_dicts is None:
        event_bytes = b""
    else:
        event_str = "\n".join([json.dumps(event) for event in event_dicts]) + "\n"
        event_bytes = event_str.encode()

    with mock.patch.object(bitcoin_computer.socket.socket, "recv") as mock_recv:
        # forces the return value on recv to the list of events given
        mock_recv.return_value = event_bytes
        mock_recv.side_effect = side_effect

        if isinstance(outcome, (int, float)):
            # ensures the proper output value
            assert bitcoin_computer.get_hashrate("15min") == outcome
        else:
            # When the statistics event is not given a TimeoutError will occur
            with pytest.raises(outcome):
                bitcoin_computer.get_hashrate("15min")


@pytest.mark.parametrize("hashrate_sample,  outcome", [
    ("5min", HASHRATE),
    ("15min", HASHRATE),
    ("60min", HASHRATE),
    ("1min", ValueError),
    (None, ValueError)])
# force all recv calls from socket to be a known payload
@mock.patch.object(bitcoin_computer.socket.socket, "connect")
@mock.patch.object(bitcoin_computer.socket.socket, "recv")
def test_get_hashrate_inputs(mock_recv, mock_connect, hashrate_sample, outcome):
    """ Ensures input values are checked and handled correctly """
    # sets up the return value for socket.recv
    mock_recv.return_value = str(json.dumps(STAT_EVENT_HASHRATE)+"\n").encode()

    # ensures the proper output value
    if isinstance(outcome, (int, float)):
        assert bitcoin_computer.get_hashrate(hashrate_sample) == outcome
    else:
        # When raises exception when invalid input is given
        with pytest.raises(outcome):
            bitcoin_computer.get_hashrate(hashrate_sample)


def test_get_hashrate_file_not_found():
    """ Ensures FileNotFoundError is raised if minerd unix sock cannot be found """
    import two1.commands.util.bitcoin_computer as bitcoin_computer
    bitcoin_computer.MINERD_SOCK = '/foo/bar'

    with pytest.raises(FileNotFoundError):
        bitcoin_computer.get_hashrate("15min")
