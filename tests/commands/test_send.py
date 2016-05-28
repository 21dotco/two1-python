"""Unit tests for `21 send`."""
import pytest
import unittest.mock as mock

import click

from two1.commands import send
from two1.commands.util import uxstring
from two1.blockchain import exceptions as bc_exceptions
from two1.wallet import exceptions as w_exceptions


@pytest.mark.unit
def test_send(patch_click, mock_wallet):
    """Test basic send functionality."""
    send_success = [dict(txid='short_txid', txn='long_txn_hex')]
    mock_wallet.send_to = mock.Mock(return_value=send_success)
    send_data = send._send(mock_wallet, 'myaddress', 10000, verbose=True)

    click.echo.call_count == 1
    assert send_data == send_success


@pytest.mark.unit
@pytest.mark.parametrize('side_effect, user_message', [
    (ValueError('Dust limit.'), 'Dust limit.'),
    (w_exceptions.WalletBalanceError(), uxstring.UxString.send_insufficient_confirmed),
    (bc_exceptions.DataProviderError('rejected'), uxstring.UxString.send_rejected)
])
def test_send_errors(patch_click, mock_wallet, side_effect, user_message):
    """Test send error paths."""
    mock_wallet.send_to = mock.Mock(side_effect=side_effect)
    with pytest.raises(click.ClickException) as exc:
        send._send(mock_wallet, 'myaddress', 10000, verbose=True)
        assert str(exc) == user_message
