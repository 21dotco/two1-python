import unittest.mock as mock
import pytest
import click

from tests import mock as mock_objects
from two1.commands import status
from two1.commands.util import uxstring


@pytest.mark.unit
@pytest.mark.parametrize('return_value, hashrate, is_mining', [
    (FileNotFoundError(), None, uxstring.UxString.status_mining_file_not_found),
    (TimeoutError(), None, uxstring.UxString.status_mining_timeout),
    (0, uxstring.UxString.status_mining_hashrate_unknown, uxstring.UxString.status_mining_success),
    (50e9, uxstring.UxString.status_mining_hashrate.format(50), uxstring.UxString.status_mining_success),
])
@mock.patch('two1.commands.status.bitcoin_computer.has_mining_chip', return_value=True)
def test_status_with_chip(
        mock_config, mock_rest_client, mock_wallet, patch_rest_client, patch_click, return_value, hashrate, is_mining):
    """Test 21 status for a user with a mining chip."""

    mock_options = dict(side_effect=return_value) if isinstance(return_value, Exception) else dict(
        return_value=return_value)
    with mock.patch('two1.commands.status.bitcoin_computer.get_hashrate', **mock_options):
        status_rv = status._status(mock_config, mock_rest_client, mock_wallet, False)

    assert mock_rest_client.mock_get_mined_satoshis.call_count == 1
    assert mock_rest_client.mock_get_earnings.call_count == 1
    assert status_rv['mining']['mined'] == mock_rest_client.mock_get_mined_satoshis.return_value
    assert status_rv['mining']['hashrate'] == hashrate
    assert status_rv['mining']['is_mining'] == is_mining
    assert status_rv['account']['username'] == mock_config.username
    assert status_rv['account']['address'] == mock_wallet.current_address
    assert status_rv['wallet']['wallet']['onchain'] == mock_wallet.BALANCE
    assert status_rv['wallet']['wallet']['twentyone_balance'] == mock_rest_client.EARNINGS
    assert status_rv['wallet']['wallet']['flushing'] == mock_rest_client.FLUSHED
    assert status_rv['wallet']['wallet']['channels_balance'] == 0

    click.echo.assert_any_call(uxstring.UxString.status_account.format(mock_config.username))
    click.echo.assert_any_call(
        uxstring.UxString.status_mining.format(status_rv['mining']['is_mining'],
                                               status_rv['mining']['hashrate'], status_rv['mining']['mined']))
    click.echo.assert_any_call(uxstring.UxString.status_wallet.format(**status_rv['wallet']['wallet']))


@pytest.mark.unit
@mock.patch('two1.commands.status.bitcoin_computer.has_mining_chip', return_value=False)
def test_status_no_chip(mock_config, mock_rest_client, mock_wallet, patch_rest_client, patch_click):
    """Test 21 status for a user without a mining chip."""
    status_rv = status._status(mock_config, mock_rest_client, mock_wallet, False)

    assert mock_rest_client.mock_get_mined_satoshis.call_count == 0
    assert mock_rest_client.mock_get_earnings.call_count == 1
    assert status_rv['mining'] == dict(mined=None, hashrate=None, is_mining=None)
    assert status_rv['account']['username'] == mock_config.username
    assert status_rv['account']['address'] == mock_wallet.current_address
    assert status_rv['wallet']['wallet']['onchain'] == mock_wallet.BALANCE
    assert status_rv['wallet']['wallet']['twentyone_balance'] == mock_rest_client.EARNINGS
    assert status_rv['wallet']['wallet']['flushing'] == mock_rest_client.FLUSHED
    assert status_rv['wallet']['wallet']['channels_balance'] == 0

    click.echo.assert_any_call(uxstring.UxString.status_account.format(mock_config.username))
    click.echo.assert_any_call(uxstring.UxString.status_wallet.format(**status_rv['wallet']['wallet']))
    for _, status_detail, _ in click.echo.mock_calls:
        assert 'Hashrate' not in status_detail
        assert 'Mined (all time)' not in status_detail


@pytest.mark.unit
@mock.patch('two1.commands.status.bitcoin_computer.has_mining_chip', return_value=True)
def test_status_detail(mock_config, mock_rest_client, mock_wallet, patch_rest_client, patch_click):
    """Test 21 status detail view."""
    with mock.patch('two1.channels.PaymentChannelClient', mock_objects.MockChannelClient):
        status_rv = status._status(mock_config, mock_rest_client, mock_wallet, True)

    assert mock_rest_client.mock_get_earnings.call_count == 1
    assert status_rv['account']['username'] == mock_config.username
    assert status_rv['account']['address'] == mock_wallet.current_address
    assert status_rv['wallet']['wallet']['onchain'] == mock_wallet.BALANCE
    assert status_rv['wallet']['wallet']['twentyone_balance'] == mock_rest_client.EARNINGS
    assert status_rv['wallet']['wallet']['flushing'] == mock_rest_client.FLUSHED
    assert status_rv['wallet']['wallet']['channels_balance'] == mock_objects.MockChannelClient.BALANCE

    click.echo.assert_any_call(uxstring.UxString.status_account.format(mock_config.username))
    click.echo.assert_any_call(uxstring.UxString.status_wallet.format(**status_rv['wallet']['wallet']))

    _, status_detail, _ = click.echo.mock_calls[3]
    assert mock_wallet.current_address in status_detail[0]
    assert mock_objects.MockChannelClient.URL in status_detail[0]
    assert str(mock_objects.MockChannelClient.BALANCE) in status_detail[0]
    assert str(mock_wallet.BALANCE) in status_detail[0]
