# standard python imports
import json
import unittest.mock as mock
import base64

# 3rd party imports
import pytest
import requests

# two1 imports
import two1
from two1.commands.util import exceptions
from two1.server import rest_client
from two1.server import machine_auth_wallet
from tests.mock import MockHttpResponse


@pytest.mark.parametrize("request_side_effect, status_code, data, raised_exception", [
    # checks early request errors
    (requests.exceptions.Timeout, None, None, exceptions.ServerConnectionError),
    (requests.exceptions.ConnectionError, None, None, exceptions.ServerConnectionError),

    # checks valid ok response from server
    (None, 200, None, None),

    # checks valid ok response from server
    (None, 301, None, exceptions.UpdateRequiredError),

    # checks 403 forbidden because api call needs bitcoin computer
    (None, 403, json.dumps({'detail': "TO100"}), exceptions.BitcoinComputerNeededError),

    # checks generic error status code with valid json data
    (None, 400, json.dumps({"test": "data"}), exceptions.ServerRequestError),

    # checks generic error status code with invalid json data
    (None, 400, "{bad: json}", exceptions.ServerRequestError),
    ])
def test_request_error_paths(mock_wallet, request_side_effect, status_code, data, raised_exception):
    # creates a machine_auth from a mock wallet
    machine_auth = machine_auth_wallet.MachineAuthWallet(mock_wallet)
    rc = rest_client.TwentyOneRestClient("", machine_auth)

    with mock.patch("two1.server.rest_client.requests.Session.request") as mock_request:
        if request_side_effect:
            mock_request.side_effect = request_side_effect
            with pytest.raises(raised_exception):
                rc._request()
        else:
            response = MockHttpResponse(status_code=status_code, data=data)
            mock_request.return_value = response
            if raised_exception:
                with pytest.raises(raised_exception) as ex_info:
                    rc._request()

                if data:
                    try:
                        json.loads(data)
                    except ValueError:
                        try:
                            json.loads(data)
                        except ValueError:
                            assert 'error' in ex_info.value.message
                        else:
                            assert 'error' in ex_info.value.data
                    else:
                        assert json.loads(data) == ex_info.value.data
            else:
                assert rc._request() == response


@pytest.mark.parametrize("device_id, data", [
    # Custom device id and adds data to check Content-Type
    ("DEVICE_ID", {'data': True}),

    # Custom device id and no data
    ("DEVICE_ID", None),

    # No device id and no data
    (None, None),
    ])
def test_check_headers(mock_wallet, device_id, data):
    # Creates a machine_auth from a mock wallet
    machine_auth = machine_auth_wallet.MachineAuthWallet(mock_wallet)
    rc = rest_client.TwentyOneRestClient("", machine_auth)

    # Forces the rest client _device_id to be parameterized
    if device_id:
        rc._device_id = device_id

    # Gets the encoded amchine auth pub key
    wallet_pk = base64.b64encode(machine_auth.public_key.compressed_bytes).decode()

    # Expected header format to be called as an input param into request
    expected_headers = {
        'User-Agent': "21/{}".format(two1.TWO1_VERSION),
        'From': "{}@{}".format(wallet_pk, device_id if device_id else "FREE_CLIENT")
        }

    # Function only adds content type when there is content
    if data:
        expected_headers['Content-Type'] = 'application/json'

    with mock.patch("two1.server.rest_client.requests.Session.request") as mock_request:
        mock_request.return_value = MockHttpResponse(status_code=200, data=None)
        rc._request(data=data)
        call_args = mock_request.call_args
        kwargs = call_args[1]
        assert 'headers' in kwargs
        for key, value in expected_headers.items():
            assert key in kwargs['headers']
            assert value == kwargs['headers'][key]


@pytest.mark.integration
def test_account_info(rest_client):
    response = rest_client.account_info()
    assert response.status_code == 200


@pytest.mark.integration
def test_get_work(logged_in_rest_client):
    response = logged_in_rest_client.get_work()
    assert response.status_code == 200


@pytest.mark.integration
def test_get_shares(logged_in_rest_client):
    shares = logged_in_rest_client.get_shares()
    assert isinstance(shares, dict)


@pytest.mark.integration
def test_get_earning_logs(logged_in_rest_client):
    logs = logged_in_rest_client.get_earning_logs()
    assert isinstance(logs, dict)


@pytest.mark.integration
def test_get_mined_satoshis(logged_in_rest_client):
    assert isinstance(logged_in_rest_client.get_mined_satoshis(), int)
