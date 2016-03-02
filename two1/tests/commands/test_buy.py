"""Unit tests for `21 buy`."""
import click
import pytest

import two1.tests.mock as mock
import two1.commands.buy as buy
import two1.commands.util.uxstring as uxstring


def test_get_buy(patch_click, mock_config, patch_bitrequests, mock_rest_client):
    """Test a standard GET buy."""
    resource = 'http://127.0.0.1:5000'
    buy._buy(mock_config, mock_rest_client, resource)

    assert patch_bitrequests.method == 'get'
    assert patch_bitrequests.url == resource
    assert patch_bitrequests.max_price == 10000
    assert len(patch_bitrequests.headers.keys()) == 0
    assert patch_bitrequests.data is None
    assert patch_bitrequests.response.status_code == 200
    assert patch_bitrequests.response.text == mock.MockBitResponse.SUCCESS_RESPONSE
    assert patch_bitrequests.response.amount_paid == mock.MockBitResponse.GET_COST
    assert patch_click.call_count == 2
    patch_click.assert_any_call(uxstring.UxString.buy_balances.format(patch_bitrequests.response.amount_paid, '21.co', mock.MockTwentyOneRestClient.EARNINGS), err=True)
    patch_click.assert_any_call(mock.MockBitResponse.SUCCESS_RESPONSE, file=None)


def test_info_buy(patch_click, mock_config, patch_bitrequests, mock_rest_client):
    """Test a information-only buy."""
    resource = 'http://127.0.0.1:5000'
    buy._buy(mock_config, mock_rest_client, resource, info_only=True)

    assert not hasattr(patch_bitrequests, 'method')
    assert not hasattr(patch_bitrequests, 'url')
    assert not hasattr(patch_bitrequests, 'max_price')
    assert not hasattr(patch_bitrequests, 'headers')
    patch_click.assert_called_once_with('\n'.join(['{}: {}'.format(k, v) for k, v in mock.MockBitRequests.HEADERS.items()]))


def test_post_url_buy(patch_click, mock_config, patch_bitrequests, mock_rest_client):
    """Test a POST buy with form url-encoded data."""
    resource = 'http://127.0.0.1:5000'
    buy._buy(mock_config, mock_rest_client, resource, data='type=test')

    assert patch_bitrequests.method == 'post'
    assert patch_bitrequests.url == resource
    assert patch_bitrequests.max_price == 10000
    assert patch_bitrequests.headers['Content-Type'] == 'application/x-www-form-urlencoded'
    assert patch_bitrequests.data['type'] == 'test'
    assert patch_bitrequests.response.status_code == 201
    assert patch_bitrequests.data['type'] in patch_bitrequests.response.text
    assert patch_bitrequests.response.amount_paid == mock.MockBitResponse.POST_COST
    assert patch_click.call_count == 2
    patch_click.assert_any_call('{"type": "test"}', file=None)
    patch_click.assert_any_call(uxstring.UxString.buy_balances.format(patch_bitrequests.response.amount_paid, '21.co', mock.MockTwentyOneRestClient.EARNINGS), err=True)


def test_post_json_buy(patch_click, mock_config, patch_bitrequests, mock_rest_client):
    """Test a POST buy with json-encoded data."""
    resource = 'http://127.0.0.1:5000'
    buy._buy(mock_config, mock_rest_client, resource, data='{"type": "test"}')

    assert patch_bitrequests.method == 'post'
    assert patch_bitrequests.url == resource
    assert patch_bitrequests.max_price == 10000
    assert patch_bitrequests.headers['Content-Type'] == 'application/json'
    assert patch_bitrequests.data['type'] == 'test'
    assert patch_bitrequests.response.status_code == 201
    assert patch_bitrequests.data['type'] in patch_bitrequests.response.text
    assert patch_bitrequests.response.amount_paid == mock.MockBitResponse.POST_COST
    assert patch_click.call_count == 2
    patch_click.assert_any_call('{"type": "test"}', file=None)
    patch_click.assert_any_call(uxstring.UxString.buy_balances.format(patch_bitrequests.response.amount_paid, '21.co', mock.MockTwentyOneRestClient.EARNINGS), err=True)

def test_buy_headers(patch_click, mock_config, patch_bitrequests, mock_rest_client):
    """Test a buy with custom headers."""
    resource = 'http://127.0.0.1:5000'
    buy._buy(mock_config, mock_rest_client, resource, header=('Authorization: Bearer MYTESTKEY',))

    assert patch_bitrequests.method == 'get'
    assert patch_bitrequests.url == resource
    assert patch_bitrequests.max_price == 10000
    assert patch_bitrequests.headers['Authorization'] == 'Bearer MYTESTKEY'
    assert patch_bitrequests.data is None
    assert patch_bitrequests.response.status_code == 200
    assert patch_bitrequests.response.text == mock.MockBitResponse.SUCCESS_RESPONSE
    assert patch_bitrequests.response.amount_paid == mock.MockBitResponse.GET_COST
    assert patch_click.call_count == 2
    patch_click.assert_any_call(mock.MockBitResponse.SUCCESS_RESPONSE, file=None)
    patch_click.assert_any_call(uxstring.UxString.buy_balances.format(patch_bitrequests.response.amount_paid, '21.co', mock.MockTwentyOneRestClient.EARNINGS), err=True)


def test_non_buy(patch_click, mock_config, patch_bitrequests, mock_rest_client):
    """Test a buy that does not hit a 402-payable endpoint."""
    resource = 'http://127.0.0.1:5000'
    buy._buy(mock_config, mock_rest_client, resource, method='put')

    assert patch_bitrequests.method == 'put'
    assert patch_bitrequests.url == resource
    assert patch_bitrequests.max_price == 10000
    assert patch_bitrequests.data is None
    assert patch_bitrequests.response.status_code == 405
    assert patch_bitrequests.response.text == mock.MockBitResponse.FAILURE_RESPONSE
    assert not hasattr(patch_bitrequests.response, 'amount_paid')
    patch_click.assert_called_once_with(mock.MockBitResponse.FAILURE_RESPONSE, file=None)


def test_error_buys(patch_click, mock_config, patch_bitrequests, mock_rest_client):
    """Test buy failure under various error cases."""
    resource = 'http://127.0.0.1:5000'

    # Test disallowed payment method
    with pytest.raises(click.ClickException) as e:
        buy._buy(mock_config, mock_rest_client, resource, payment_method='fake')
    assert str(e.value) == uxstring.UxString.buy_bad_payment_method.format('fake')

    # Test improper resource URL
    with pytest.raises(click.ClickException) as e:
        buy._buy(mock_config, mock_rest_client, '127.0.0.1:5000')
    assert str(e.value) == uxstring.UxString.buy_bad_uri_scheme

    # Test improper resource URL
    with pytest.raises(click.ClickException) as e:
        buy._buy(mock_config, mock_rest_client, 'http://')
    assert str(e.value) == uxstring.UxString.buy_bad_uri_host

    assert patch_click.called is False


def test_parse_post_data():
    """Test utility functionality for parsing data."""
    form_url = 'type=test&message=hey hey hey!'
    json = '{"type": "test", "message": "hey hey hey!"}'
    invalid = 'type: test; message: hey hey hey!'

    data_dict, content_type = buy._parse_post_data(form_url)
    assert isinstance(data_dict, dict)
    assert data_dict['type'] == 'test'
    assert data_dict['message'] == 'hey hey hey!'
    assert content_type == 'application/x-www-form-urlencoded'

    data_dict, content_type = buy._parse_post_data(json)
    assert isinstance(data_dict, dict)
    assert data_dict['type'] == 'test'
    assert data_dict['message'] == 'hey hey hey!'
    assert content_type == 'application/json'

    with pytest.raises(click.ClickException) as e:
        data_dict, content_type = buy._parse_post_data(invalid)
    assert str(e.value) == uxstring.UxString.buy_bad_data_format
