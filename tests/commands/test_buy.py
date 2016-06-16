"""Unit tests for `21 buy`."""
import json
import click
import pytest
import unittest.mock

import tests.mock as mock
import two1.commands.buy as buy
import two1.commands.util.uxstring as uxstring


@pytest.mark.parametrize('method, balance_str, balance_int', [
    ('offchain', '21.co', mock.MockTwentyOneRestClient.EARNINGS),
    ('onchain', 'blockchain', mock.MockTwo1Wallet.BALANCE - mock.MockBitResponse.GET_COST),
    ('channel', 'payment channels', 0),
])
@unittest.mock.patch('click.confirm', unittest.mock.Mock(return_value=True))
def test_get_buy(patch_click, mock_config, mock_machine_auth, patch_bitrequests, mock_rest_client,
                 method, balance_str, balance_int):
    """Test a standard GET buy with all payment methods."""
    resource = 'http://127.0.0.1:5000'
    buy._buy(mock_config, mock_rest_client, mock_machine_auth, resource, payment_method=method)

    assert patch_bitrequests.method == 'get'
    assert patch_bitrequests.url == resource
    assert patch_bitrequests.max_price == 10000
    assert len(patch_bitrequests.headers.keys()) == 0
    assert patch_bitrequests.data is None
    assert patch_bitrequests.response.status_code == 200
    assert patch_bitrequests.response.text == mock.MockBitResponse.SUCCESS_RESPONSE
    assert patch_bitrequests.response.amount_paid == mock.MockBitResponse.GET_COST
    assert click.echo.call_count == 3
    click.echo.assert_any_call(uxstring.UxString.buy_balances.format(
        patch_bitrequests.response.amount_paid, balance_str, balance_int), err=True)
    click.echo.assert_any_call(mock.MockBitResponse.SUCCESS_RESPONSE, nl=False)


def test_info_buy(patch_click, mock_config, mock_machine_auth, patch_bitrequests, mock_rest_client):
    """Test a information-only buy."""
    resource = 'http://127.0.0.1:5000'
    buy._buy(mock_config, mock_rest_client, mock_machine_auth, resource, info_only=True)

    assert not hasattr(patch_bitrequests, 'method')
    assert not hasattr(patch_bitrequests, 'url')
    assert not hasattr(patch_bitrequests, 'max_price')
    assert not hasattr(patch_bitrequests, 'headers')
    click.echo.assert_called_once_with(
        '\n'.join(['{}: {}'.format(k, v) for k, v in mock.MockBitRequests.HEADERS.items()]))


def test_post_url_buy(patch_click, mock_config, mock_machine_auth, patch_bitrequests, mock_rest_client):
    """Test a POST buy with form url-encoded data."""
    resource = 'http://127.0.0.1:5000'
    buy._buy(mock_config, mock_rest_client, mock_machine_auth, resource, data='type=test')

    assert patch_bitrequests.method == 'post'
    assert patch_bitrequests.url == resource
    assert patch_bitrequests.max_price == 10000
    assert patch_bitrequests.headers['Content-Type'] == 'application/x-www-form-urlencoded'
    assert patch_bitrequests.data == 'type=test'
    assert patch_bitrequests.response.status_code == 201
    assert 'test' in patch_bitrequests.response.text
    assert patch_bitrequests.response.amount_paid == mock.MockBitResponse.POST_COST
    assert click.echo.call_count == 3
    click.echo.assert_any_call(uxstring.UxString.buy_balances.format(
        patch_bitrequests.response.amount_paid, '21.co', mock.MockTwentyOneRestClient.EARNINGS), err=True)


def test_post_json_buy(patch_click, mock_config, mock_machine_auth, patch_bitrequests, mock_rest_client):
    """Test a POST buy with json-encoded data."""
    resource = 'http://127.0.0.1:5000'
    buy._buy(mock_config, mock_rest_client, mock_machine_auth, resource, data='{"type": "test"}')
    data_dict = json.loads(patch_bitrequests.data)

    assert patch_bitrequests.method == 'post'
    assert patch_bitrequests.url == resource
    assert patch_bitrequests.max_price == 10000
    assert patch_bitrequests.headers['Content-Type'] == 'application/json'
    assert data_dict['type'] == 'test'
    assert patch_bitrequests.response.status_code == 201
    assert data_dict['type'] in patch_bitrequests.response.text
    assert patch_bitrequests.response.amount_paid == mock.MockBitResponse.POST_COST
    assert click.echo.call_count == 3
    click.echo.assert_any_call(uxstring.UxString.buy_balances.format(
        patch_bitrequests.response.amount_paid, '21.co', mock.MockTwentyOneRestClient.EARNINGS), err=True)


def test_buy_headers(patch_click, mock_config, mock_machine_auth, patch_bitrequests, mock_rest_client):
    """Test a buy with custom headers."""
    resource = 'http://127.0.0.1:5000'
    buy._buy(mock_config, mock_rest_client, mock_machine_auth, resource, header=('Authorization: Bearer MYTESTKEY',))

    assert patch_bitrequests.method == 'get'
    assert patch_bitrequests.url == resource
    assert patch_bitrequests.max_price == 10000
    assert patch_bitrequests.headers['Authorization'] == 'Bearer MYTESTKEY'
    assert patch_bitrequests.data is None
    assert patch_bitrequests.response.status_code == 200
    assert patch_bitrequests.response.text == mock.MockBitResponse.SUCCESS_RESPONSE
    assert patch_bitrequests.response.amount_paid == mock.MockBitResponse.GET_COST
    assert click.echo.call_count == 3
    click.echo.assert_any_call(mock.MockBitResponse.SUCCESS_RESPONSE, nl=False)
    click.echo.assert_any_call(uxstring.UxString.buy_balances.format(
        patch_bitrequests.response.amount_paid, '21.co', mock.MockTwentyOneRestClient.EARNINGS), err=True)


def test_non_buy(patch_click, mock_config, mock_machine_auth, patch_bitrequests, mock_rest_client):
    """Test a buy that does not hit a 402-payable endpoint."""
    resource = 'http://127.0.0.1:5000'
    with pytest.raises(SystemExit):
        buy._buy(mock_config, mock_rest_client, mock_machine_auth, resource, method='put')

    assert patch_bitrequests.method == 'put'
    assert patch_bitrequests.url == resource
    assert patch_bitrequests.max_price == 10000
    assert patch_bitrequests.data is None
    assert patch_bitrequests.response.status_code == 405
    assert patch_bitrequests.response.text == mock.MockBitResponse.FAILURE_RESPONSE
    assert not hasattr(patch_bitrequests.response, 'amount_paid')
    assert click.echo.call_count == 2
    click.echo.assert_any_call(mock.MockBitResponse.FAILURE_RESPONSE, nl=False)


def test_error_buys(patch_click, mock_config, mock_machine_auth, patch_bitrequests, mock_rest_client):
    """Test buy failure under various error cases."""
    resource = 'http://127.0.0.1:5000'

    # Test disallowed payment method
    with pytest.raises(click.ClickException) as e:
        buy._buy(mock_config, mock_rest_client, mock_machine_auth, resource, payment_method='fake')
    assert str(e.value) == uxstring.UxString.buy_bad_payment_method.format('fake')

    assert click.echo.called is False


def test_parse_post_data():
    """Test utility functionality for parsing data."""
    form_url = 'type=test&message=hey hey hey!'
    json_data = '{"type": "test", "message": "hey hey hey!"}'
    invalid = 'type: test; message: hey hey hey!'

    data_str, content_type = buy._parse_post_data(form_url)
    assert isinstance(data_str, str)
    assert 'type=test' in data_str
    assert 'message=hey hey hey!' in data_str
    assert content_type == 'application/x-www-form-urlencoded'

    data_str, content_type = buy._parse_post_data(json_data)
    data_dict = json.loads(data_str)
    assert isinstance(data_str, str)
    assert data_dict['type'] == 'test'
    assert data_dict['message'] == 'hey hey hey!'
    assert content_type == 'application/json'

    with pytest.raises(click.ClickException) as e:
        data_dict, content_type = buy._parse_post_data(invalid)
    assert str(e.value) == uxstring.UxString.buy_bad_data_format
