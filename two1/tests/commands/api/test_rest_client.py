import json
import pytest
import requests
import unittest.mock as mock

from two1.commands.util import exceptions
from two1.lib.server import rest_client
from two1.lib.server import machine_auth_wallet
from two1.commands.util import exceptions
from two1.tests.mock import MockHttpResponse

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
    (None, 300, json.dumps({"test": "data"}), exceptions.ServerRequestError),

    # checks generic error status code with invalid json data
    (None, 300, "{bad: json}", exceptions.ServerRequestError),
    ])
def test_request_error_paths(mock_wallet, request_side_effect, status_code, data, raised_exception):
    # creates a machine_auth from a mock wallet
    machine_auth = machine_auth_wallet.MachineAuthWallet(mock_wallet)
    rc = rest_client.TwentyOneRestClient("", machine_auth)

    with mock.patch("two1.lib.server.rest_client.requests.Session.request") as mock_request:
        if request_side_effect:
            mock_request.side_effect = request_side_effect
            with pytest.raises(raised_exception):
               rc._request()
        else:
            response = MockHttpResponse(status_code=status_code, data=data)
            mock_request.return_value = response
            if raised_exception:
                with pytest.raises(raised_exception):
                   rc._request()
            else:
                assert rc._request() == response

